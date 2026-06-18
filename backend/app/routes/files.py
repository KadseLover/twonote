from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlmodel import Session

from app.database import get_session
from app.models.file import FileRecord  # noqa: F401  (Tabelle registrieren)
from app.models.user import User
from app.services import storage as storage_service
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/files", tags=["files"])

# Akzeptierte Upload-MIME-Types. Alle werden im OnlyOffice-Editor geöffnet
# (Word/Excel/PowerPoint im jeweiligen Co-Editing-Modus, PDF im PDF-Editor).
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/msword",  # .doc
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/vnd.ms-excel",  # .xls
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # .pptx
    "application/vnd.ms-powerpoint",  # .ppt
}

# Endung → MIME-Type, falls der Browser keinen (passenden) content_type mitschickt.
_EXT_TO_MIME = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ppt": "application/vnd.ms-powerpoint",
}


class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[str] = None


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
        ext = "." + name_lower.rsplit(".", 1)[-1] if "." in name_lower else ""
        if ext in _EXT_TO_MIME:
            content_type = _EXT_TO_MIME[ext]
        else:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Nur PDF-, Word-, Excel- und PowerPoint-Dateien werden akzeptiert",
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
