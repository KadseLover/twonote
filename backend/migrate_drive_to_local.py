"""Einmalige Migration: Google Drive → lokale Server-Speicherung.

Lädt den kompletten Drive-Ordnerbaum (ab GOOGLE_DRIVE_FOLDER_ID) herunter und
legt ihn lokal an:
  - pro Drive-Datei/-Ordner ein ``FileRecord`` in der DB, **ID = original Drive-ID**
  - Datei-Bytes unter ``data/files/{drive_id}``

Weil die Drive-IDs unverändert übernommen werden, bleiben bestehende
``Annotation.file_id`` / ``Summary.file_id`` ohne Umschlüsselung gültig.

Voraussetzung: Die Google-Credentials stehen noch in ``.env``
(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN, GOOGLE_DRIVE_FOLDER_ID)
und die google-* Pakete sind installiert. Das Skript ist idempotent –
bereits angelegte Einträge werden übersprungen.

Aufruf:  cd backend && python migrate_drive_to_local.py
"""

import io
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

# App-Imports (unabhängig von Drive)
from app.database import create_db_and_tables, engine
from app.models.file import FileRecord
from app.services import storage as storage_service
from sqlmodel import Session

load_dotenv()

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN", "")
ROOT_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")

DRIVE_FOLDER_MIME = "application/vnd.google-apps.folder"
SCOPES = ["https://www.googleapis.com/auth/drive"]


def _get_drive_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _list_children(service, folder_id: str) -> list[dict]:
    query = f"'{folder_id}' in parents and trashed = false"
    files: list[dict] = []
    page_token = None
    while True:
        resp = (
            service.files()
            .list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType, modifiedTime, size)",
                orderBy="folder,modifiedTime desc",
                pageToken=page_token,
            )
            .execute()
        )
        files.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return files


def _download_bytes(service, file_id: str) -> bytes:
    from googleapiclient.http import MediaIoBaseDownload

    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buffer.seek(0)
    return buffer.read()


def _parse_time(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


def _migrate_folder(service, session: Session, drive_folder_id: str, local_parent_id):
    """Migriert rekursiv alle Kinder eines Drive-Ordners."""
    for item in _list_children(service, drive_folder_id):
        drive_id = item["id"]
        is_folder = item.get("mimeType") == DRIVE_FOLDER_MIME

        if session.get(FileRecord, drive_id) is not None:
            print(f"  übersprungen (existiert): {item['name']} [{drive_id}]")
            if is_folder:
                _migrate_folder(service, session, drive_id, drive_id)
            continue

        mtime = _parse_time(item.get("modifiedTime"))
        if is_folder:
            record = FileRecord(
                id=drive_id,
                name=item["name"],
                parent_id=local_parent_id,
                is_folder=True,
                created_at=mtime,
                modified_at=mtime,
            )
            session.add(record)
            session.commit()
            print(f"  Ordner: {item['name']} [{drive_id}]")
            _migrate_folder(service, session, drive_id, drive_id)
        else:
            content = _download_bytes(service, drive_id)
            storage_service._ensure_dir()
            with open(storage_service._blob_path(drive_id), "wb") as f:
                f.write(content)
            record = FileRecord(
                id=drive_id,
                name=item["name"],
                parent_id=local_parent_id,
                is_folder=False,
                mime_type=item.get("mimeType", "application/octet-stream"),
                size=len(content),
                created_at=mtime,
                modified_at=mtime,
            )
            session.add(record)
            session.commit()
            print(f"  Datei:  {item['name']} ({len(content)} Bytes) [{drive_id}]")


def main() -> int:
    if not (CLIENT_ID and CLIENT_SECRET and REFRESH_TOKEN and ROOT_FOLDER_ID):
        print(
            "FEHLER: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN "
            "und GOOGLE_DRIVE_FOLDER_ID müssen in .env gesetzt sein.",
            file=sys.stderr,
        )
        return 1

    print("Stelle Verbindung zu Google Drive her …")
    service = _get_drive_service()

    print("Lege DB-Tabellen an (falls nötig) …")
    create_db_and_tables()

    print(f"Migriere Drive-Ordner {ROOT_FOLDER_ID} → data/files/ …")
    with Session(engine) as session:
        _migrate_folder(service, session, ROOT_FOLDER_ID, None)

    print("Fertig. Migration abgeschlossen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
