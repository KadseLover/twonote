from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel

from app.models.user import User
from app.services import drive as drive_service
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


@router.get("", summary="Dateien und Ordner aus Drive listen")
def list_files(
    folder_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """Gibt alle Dateien und Unterordner im angegebenen Drive-Ordner zurück."""
    try:
        files = drive_service.list_files(folder_id)
        return {"files": files}
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@router.post("/folder", status_code=status.HTTP_201_CREATED, summary="Ordner erstellen")
def create_folder(
    body: FolderCreate,
    current_user: User = Depends(get_current_user),
):
    """Erstellt einen neuen Ordner in Drive."""
    try:
        folder = drive_service.create_folder(body.name, body.parent_id)
        return {"folder": folder}
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@router.post("/upload", status_code=status.HTTP_201_CREATED, summary="Datei hochladen")
async def upload_file(
    file: UploadFile = File(...),
    folder_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """
    Lädt eine PDF- oder Word-Datei in den Drive-Ordner hoch.
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
        uploaded = drive_service.upload_file(content, file.filename, content_type, folder_id)
        return {"file": uploaded, "message": f"'{file.filename}' erfolgreich hochgeladen"}
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@router.get("/{file_id}/download", summary="Datei herunterladen")
def download_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
):
    """Lädt eine Datei aus Drive herunter und gibt sie als Byte-Stream zurück."""
    try:
        content, filename, mime_type = drive_service.download_file(file_id)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datei '{file_id}' nicht gefunden",
        )

    return Response(
        content=content,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
        },
    )


@router.put("/{file_id}", summary="Datei aktualisieren (Inhalt ersetzen)")
async def update_file(
    file_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Überschreibt den Inhalt einer bestehenden Drive-Datei.
    Wird vom PDF-Editor zum Speichern von Annotationen verwendet.
    """
    # Prüfen ob Datei existiert
    meta = drive_service.get_file_meta(file_id)
    if not meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datei '{file_id}' nicht gefunden",
        )

    content_type = file.content_type or meta.get("mimeType", "application/pdf")
    content = await file.read()

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Die Datei ist leer",
        )

    try:
        updated = drive_service.update_file(file_id, content, content_type)
        return {"file": updated, "message": "Datei erfolgreich aktualisiert"}
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Datei löschen")
def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
):
    """Löscht eine Datei aus Drive."""
    meta = drive_service.get_file_meta(file_id)
    if not meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datei '{file_id}' nicht gefunden",
        )

    try:
        drive_service.delete_file(file_id)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
