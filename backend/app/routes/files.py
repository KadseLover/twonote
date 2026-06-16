from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlmodel import Session

from app.database import get_session
from app.models.annotation import Annotation  # noqa: F401  (Tabelle registrieren)
from app.models.file import FileRecord  # noqa: F401  (Tabelle registrieren)
from app.models.user import User
from app.services import annotations as annotations_service
from app.services import storage as storage_service
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/files", tags=["files"])

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}


class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[str] = None


class AnnotationBody(BaseModel):
    data: str  # fabric-Canvas als JSON-String
    label: Optional[str] = None  # selbst vergebener Versionsname (nur beim Anlegen)


@router.get("", summary="Dateien und Ordner listen")
def list_files(
    folder_id: Optional[str] = Query(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Gibt alle Dateien und Unterordner im angegebenen Ordner zurück."""
    try:
        files = storage_service.list_files(session, folder_id)
        return {"files": files}
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@router.post("/folder", status_code=status.HTTP_201_CREATED, summary="Ordner erstellen")
def create_folder(
    body: FolderCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Erstellt einen neuen Ordner."""
    try:
        folder = storage_service.create_folder(session, body.name, body.parent_id)
        return {"folder": folder}
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@router.post("/upload", status_code=status.HTTP_201_CREATED, summary="Datei hochladen")
async def upload_file(
    file: UploadFile = File(...),
    folder_id: Optional[str] = Query(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Lädt eine PDF- oder Word-Datei lokal in den angegebenen Ordner hoch.
    Akzeptiert: application/pdf, .docx, .doc
    """
    content_type = file.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES:
        name_lower = (file.filename or "").lower()
        if name_lower.endswith(".pdf"):
            content_type = "application/pdf"
        elif name_lower.endswith(".docx"):
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif name_lower.endswith(".doc"):
            content_type = "application/msword"
        else:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Nur PDF und Word-Dokumente (.pdf, .docx, .doc) werden akzeptiert",
            )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Die Datei ist leer",
        )

    try:
        uploaded = storage_service.upload_file(session, content, file.filename, content_type, folder_id)
        return {"file": uploaded, "message": f"'{file.filename}' erfolgreich hochgeladen"}
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


def _file_response(content: bytes, filename: str, mime_type: str) -> Response:
    """Baut eine Datei-Antwort mit RFC-5987-konformem Content-Disposition.

    HTTP-Header dürfen nur latin-1 enthalten – Umlaute/Sonderzeichen im
    Dateinamen würden sonst einen 500er auslösen.
    """
    ascii_fallback = (filename or "download").encode("ascii", "replace").decode("ascii").replace('"', "")
    utf8_filename = quote(filename or "download")
    content_disposition = (
        f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{utf8_filename}"
    )

    return Response(
        content=content,
        media_type=mime_type,
        headers={
            "Content-Disposition": content_disposition,
            "Content-Length": str(len(content)),
        },
    )


@router.get("/{file_id}/download", summary="Datei herunterladen")
def download_file(
    file_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Lädt eine Datei von der Platte herunter und gibt sie als Byte-Stream zurück."""
    try:
        content, filename, mime_type = storage_service.download_file(session, file_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datei '{file_id}' nicht gefunden",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    return _file_response(content, filename, mime_type)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Datei löschen")
def delete_file(
    file_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Löscht eine Datei lokal."""
    meta = storage_service.get_file_meta(session, file_id)
    if not meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datei '{file_id}' nicht gefunden",
        )

    try:
        storage_service.delete_file(session, file_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datei '{file_id}' nicht gefunden",
        )
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@router.get("/{file_id}/annotations", summary="Notiz-Stände (Versionen) einer Datei listen")
def list_annotations(
    file_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Gibt die Metadaten aller Notiz-Stände zurück (ohne data), neueste zuerst."""
    rows = annotations_service.list_for_file(session, file_id)
    versions = [
        {"id": r.id, "label": r.label, "created_at": r.created_at, "updated_at": r.updated_at}
        for r in rows
    ]
    return {"versions": versions, "latest_id": versions[0]["id"] if versions else None}


@router.post(
    "/{file_id}/annotations",
    status_code=status.HTTP_201_CREATED,
    summary="Neuen Notiz-Stand anlegen",
)
def create_annotation(
    file_id: str,
    body: AnnotationBody,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Legt einen neuen, eigenständigen Notiz-Stand an."""
    row = annotations_service.create_version(session, file_id, body.data, body.label or "")
    return {"id": row.id, "label": row.label, "created_at": row.created_at, "updated_at": row.updated_at}


@router.get("/{file_id}/annotations/{version_id}", summary="Einen Notiz-Stand laden")
def get_annotation(
    file_id: str,
    version_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Gibt einen bestimmten Notiz-Stand inkl. fabric-JSON zurück."""
    row = annotations_service.get_version(session, version_id)
    if row is None or row.file_id != file_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notiz-Stand nicht gefunden",
        )
    return {"id": row.id, "data": row.data, "updated_at": row.updated_at}


@router.put("/{file_id}/annotations/{version_id}", summary="Notiz-Stand überschreiben")
def update_annotation(
    file_id: str,
    version_id: int,
    body: AnnotationBody,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Überschreibt einen bestehenden Notiz-Stand."""
    row = annotations_service.get_version(session, version_id)
    if row is None or row.file_id != file_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notiz-Stand nicht gefunden",
        )
    annotations_service.update_version(session, version_id, body.data)
    return {"status": "ok"}
