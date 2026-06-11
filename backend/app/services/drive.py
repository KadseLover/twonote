import io
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from app.config import settings

SCOPES = ["https://www.googleapis.com/auth/drive"]

_credentials: Optional[Credentials] = None


def _get_drive_service():
    """Erstellt und gibt einen authentifizierten Google Drive API Client zurück."""
    global _credentials

    if not settings.drive_oauth2_configured:
        raise RuntimeError(
            "Google Drive OAuth2 nicht konfiguriert. "
            "Bitte GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET und GOOGLE_REFRESH_TOKEN in .env setzen "
            "und get_refresh_token.py ausführen."
        )

    try:
        if _credentials is None:
            _credentials = Credentials(
                token=None,
                refresh_token=settings.google_refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
                scopes=SCOPES,
            )

        if not _credentials.valid:
            _credentials.refresh(Request())

        return build("drive", "v3", credentials=_credentials, cache_discovery=False)
    except Exception as e:
        _credentials = None
        raise RuntimeError(f"Google Drive Verbindung fehlgeschlagen: {e}") from e


def list_files(folder_id: str | None = None) -> list[dict]:
    """
    Listet alle Dateien und Unterordner im angegebenen Drive-Ordner auf.
    Ordner erscheinen vor Dateien (clientseitig sortiert).
    """
    service = _get_drive_service()
    target = folder_id or settings.google_drive_folder_id

    if not target:
        raise RuntimeError(
            "GOOGLE_DRIVE_FOLDER_ID nicht konfiguriert. Bitte in .env setzen."
        )

    query = f"'{target}' in parents and trashed = false"

    try:
        results = (
            service.files()
            .list(
                q=query,
                fields="files(id, name, mimeType, modifiedTime, size)",
                orderBy="folder,modifiedTime desc",
            )
            .execute()
        )
        return results.get("files", [])
    except Exception as e:
        raise RuntimeError(f"Dateien konnten nicht geladen werden: {e}") from e


def create_folder(name: str, parent_id: str | None = None) -> dict:
    """Erstellt einen neuen Ordner in Drive und gibt seine Metadaten zurück."""
    service = _get_drive_service()
    target_folder = parent_id or settings.google_drive_folder_id

    if not target_folder:
        raise RuntimeError(
            "GOOGLE_DRIVE_FOLDER_ID nicht konfiguriert. Bitte in .env setzen."
        )

    file_metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [target_folder],
    }
    try:
        folder = (
            service.files()
            .create(
                body=file_metadata,
                fields="id, name, mimeType, modifiedTime",
            )
            .execute()
        )
        return folder
    except Exception as e:
        raise RuntimeError(f"Ordner konnte nicht erstellt werden: {e}") from e


def upload_file(
    file_content: bytes,
    filename: str,
    mime_type: str,
    folder_id: str | None = None,
) -> dict:
    """
    Lädt eine Datei in den angegebenen Drive-Ordner hoch (Standard: Root-Ordner).
    Gibt die Metadaten der hochgeladenen Datei zurück.
    """
    service = _get_drive_service()
    target_folder = folder_id or settings.google_drive_folder_id

    file_metadata = {
        "name": filename,
        "parents": [target_folder],
    }

    media = MediaIoBaseUpload(
        io.BytesIO(file_content),
        mimetype=mime_type,
        resumable=True,
    )

    try:
        file = (
            service.files()
            .create(
                body=file_metadata,
                media_body=media,
                fields="id, name, mimeType, modifiedTime, size",
            )
            .execute()
        )
        return file
    except Exception as e:
        raise RuntimeError(f"Upload fehlgeschlagen: {e}") from e


def download_file(file_id: str) -> tuple[bytes, str, str]:
    """
    Lädt eine Datei aus Drive herunter.
    Gibt (Inhalt als bytes, Dateiname, MIME-Type) zurück.
    """
    service = _get_drive_service()

    try:
        file_meta = (
            service.files()
            .get(fileId=file_id, fields="name, mimeType")
            .execute()
        )

        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        buffer.seek(0)
        return buffer.read(), file_meta["name"], file_meta["mimeType"]
    except Exception as e:
        raise RuntimeError(f"Download fehlgeschlagen: {e}") from e


def update_file(file_id: str, file_content: bytes, mime_type: str) -> dict:
    """
    Überschreibt den Inhalt einer bestehenden Drive-Datei.
    Gibt die aktualisierten Metadaten zurück.
    """
    service = _get_drive_service()

    media = MediaIoBaseUpload(
        io.BytesIO(file_content),
        mimetype=mime_type,
        resumable=True,
    )

    try:
        updated_file = (
            service.files()
            .update(
                fileId=file_id,
                media_body=media,
                fields="id, name, mimeType, modifiedTime, size",
            )
            .execute()
        )
        return updated_file
    except Exception as e:
        raise RuntimeError(f"Datei-Update fehlgeschlagen: {e}") from e


def delete_file(file_id: str) -> None:
    """Löscht eine Datei aus Drive (verschiebt sie in den Papierkorb)."""
    service = _get_drive_service()
    try:
        service.files().delete(fileId=file_id).execute()
    except Exception as e:
        raise RuntimeError(f"Löschen fehlgeschlagen: {e}") from e


def get_file_meta(file_id: str) -> Optional[dict]:
    """Gibt die Metadaten einer Drive-Datei zurück, oder None wenn nicht gefunden."""
    service = _get_drive_service()
    try:
        return (
            service.files()
            .get(fileId=file_id, fields="id, name, mimeType, modifiedTime, size")
            .execute()
        )
    except HttpError as e:
        if e.resp.status == 404:
            return None
        raise RuntimeError(f"Metadaten konnten nicht geladen werden: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Metadaten konnten nicht geladen werden: {e}") from e
