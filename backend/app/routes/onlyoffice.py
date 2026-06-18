"""OnlyOffice-Integration: Editor-Config, server-zu-server Download & Speicher-Callback.

Ablauf:
- Der Browser holt sich über ``/onlyoffice/config`` (App-Auth) die signierte Editor-Config
  inkl. der öffentlichen Document-Server-URL und startet damit den OnlyOffice-Editor.
- Der Document Server lädt die Originaldatei server-zu-server über ``/onlyoffice/download``
  und meldet Speicherstände an ``/onlyoffice/callback`` – beide URLs zeigen auf
  ``BACKEND_INTERNAL_URL`` (Docker-Netz), nicht auf das öffentliche Frontend.

Auth-Schichten:
- Unsere eigenen, signierten ``?token=``-Werte beweisen, dass Download-/Callback-URL von uns
  stammen (Download- und Callback-Endpunkte haben keine App-Session).
- Zusätzlich signiert der Document Server seine Config/Callbacks mit ``ONLYOFFICE_JWT_SECRET``;
  das prüfen wir beim Callback (Authorization-Header bzw. Token im Body).
"""

import hashlib
import logging
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, Response
from jose import JWTError, jwt
from sqlmodel import Session

from app.config import settings
from app.database import get_session
from app.models.file import FileRecord
from app.models.user import User
from app.services import storage as storage_service
from app.services.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/files", tags=["onlyoffice"])

# Speicher-relevante Callback-Status: 2 = MustSave (alle haben geschlossen),
# 6 = ForceSave (während des Editierens angefordert).
_SAVE_STATUSES = {2, 6}
_ALGO = "HS256"


def _url_secret() -> str:
    """Geheimnis für unsere eigenen Download-/Callback-URL-Token."""
    return settings.onlyoffice_jwt_secret or settings.jwt_secret_key


def _make_url_token(file_id: str, purpose: str, expires_minutes: Optional[int]) -> str:
    payload: dict = {"file_id": file_id, "purpose": purpose}
    if expires_minutes is not None:
        payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    return jwt.encode(payload, _url_secret(), algorithm=_ALGO)


def _verify_url_token(token: str, file_id: str, purpose: str) -> None:
    try:
        payload = jwt.decode(token, _url_secret(), algorithms=[_ALGO])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ungültiger Token")
    if payload.get("file_id") != file_id or payload.get("purpose") != purpose:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token passt nicht")


def _doc_key(file_id: str, modified_at: datetime) -> str:
    """Stabiler Co-Editing-Schlüssel: gleich während einer Sitzung, neu nach jedem Speichern."""
    raw = f"{file_id}:{modified_at}"
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def _require_file(session: Session, file_id: str) -> FileRecord:
    record = session.get(FileRecord, file_id)
    if record is None or record.is_folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Datei nicht gefunden")
    return record


@router.get("/{file_id}/onlyoffice/config", summary="OnlyOffice-Editor-Config")
def onlyoffice_config(
    file_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Baut die (ggf. signierte) Editor-Config für den Browser."""
    record = _require_file(session, file_id)
    document_type, file_type, editable = storage_service.editor_meta(record.name)

    base = settings.backend_internal_url.rstrip("/")
    download_url = (
        f"{base}/api/files/{file_id}/onlyoffice/download"
        f"?token={_make_url_token(file_id, 'download', expires_minutes=60)}"
    )
    # Callback kann erst nach langer Editiersitzung kommen → kein kurzes Ablaufdatum.
    callback_url = (
        f"{base}/api/files/{file_id}/onlyoffice/callback"
        f"?token={_make_url_token(file_id, 'callback', expires_minutes=None)}"
    )

    config: dict = {
        "document": {
            "fileType": file_type,
            "key": _doc_key(file_id, record.modified_at),
            "title": record.name,
            "url": download_url,
            "permissions": {"edit": editable, "download": True},
        },
        "documentType": document_type,
        "editorConfig": {
            "mode": "edit" if editable else "view",
            "lang": "de",
            "callbackUrl": callback_url,
            "user": {"id": str(current_user.id), "name": current_user.username},
        },
    }

    if settings.onlyoffice_jwt_secret:
        config["token"] = jwt.encode(config, settings.onlyoffice_jwt_secret, algorithm=_ALGO)

    return {"documentServerUrl": settings.onlyoffice_public_url, "config": config}


@router.get("/{file_id}/onlyoffice/download", summary="Datei für den Document Server")
def onlyoffice_download(
    file_id: str,
    token: str = Query(...),
    session: Session = Depends(get_session),
):
    """Server-zu-server Download (keine App-Session, nur signierter URL-Token)."""
    _verify_url_token(token, file_id, "download")
    try:
        content, _filename, mime_type = storage_service.download_file(session, file_id)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Datei nicht gefunden")
    return Response(content=content, media_type=mime_type or "application/octet-stream")


@router.post("/{file_id}/onlyoffice/callback", summary="Speicher-Callback des Document Servers")
async def onlyoffice_callback(
    file_id: str,
    request: Request,
    token: str = Query(...),
    session: Session = Depends(get_session),
):
    """Verarbeitet Statusmeldungen des Document Servers und speichert bei Status 2/6 zurück."""
    _verify_url_token(token, file_id, "callback")

    body = await request.json()

    # Bei aktivem JWT signiert der Document Server den Callback – verifizieren und die
    # signierten Daten (statt des rohen Bodys) verwenden.
    if settings.onlyoffice_jwt_secret:
        auth_header = request.headers.get("Authorization", "")
        ds_token = auth_header[7:] if auth_header.startswith("Bearer ") else body.get("token")
        if not ds_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Kein OnlyOffice-Token")
        try:
            decoded = jwt.decode(ds_token, settings.onlyoffice_jwt_secret, algorithms=[_ALGO])
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="OnlyOffice-Token ungültig")
        # Der Token-Payload kapselt den Callback-Body unter "payload" (neuere Versionen)
        # oder enthält die Felder direkt (ältere Versionen).
        body = decoded.get("payload", decoded)

    callback_status = body.get("status")

    if callback_status in _SAVE_STATUSES:
        download_url = body.get("url")
        if not download_url:
            logger.warning("OnlyOffice-Callback für %s ohne url (status %s)", file_id, callback_status)
            return JSONResponse({"error": 1})
        try:
            with urllib.request.urlopen(download_url, timeout=60) as resp:  # noqa: S310 (interne DS-URL)
                content = resp.read()
            storage_service.save_content(session, file_id, content)
            logger.info("OnlyOffice: Datei %s gespeichert (status %s)", file_id, callback_status)
        except Exception as e:  # noqa: BLE001 – DS erwartet error!=0 bei Misserfolg
            logger.error("OnlyOffice-Speichern für %s fehlgeschlagen: %s", file_id, e)
            return JSONResponse({"error": 1})

    return JSONResponse({"error": 0})
