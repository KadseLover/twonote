"""Lokale Datei-Speicherung auf der Server-Platte (ersetzt Google Drive).

Datei-Metadaten (Name, Ordner-Hierarchie, Größe …) liegen in der ``file``-Tabelle
(`app.models.file.FileRecord`), die rohen Bytes flach unter ``data/files/{id}``.
Ordner sind reine DB-Einträge ohne Bytes.
"""

import os
from typing import Optional

from sqlmodel import Session, select

from app.models.file import FileRecord

# MIME-Type, an dem das Frontend Ordner erkennt.
FOLDER_MIME = "application/vnd.twonote.folder"

# Basisverzeichnis für die rohen Datei-Bytes (relativ zum Arbeitsverzeichnis des
# Backends, identisch zur SQLite-DB unter data/).
FILES_DIR = os.path.join("data", "files")


def _blob_path(file_id: str) -> str:
    return os.path.join(FILES_DIR, file_id)


def _ensure_dir() -> None:
    os.makedirs(FILES_DIR, exist_ok=True)


def _to_dict(record: FileRecord) -> dict:
    """Wandelt einen FileRecord in das vom Frontend erwartete Format um.

    Spiegelt die frühere Google-Drive-Antwort (id, name, mimeType, modifiedTime,
    size), damit das Frontend unverändert bleibt.
    """
    return {
        "id": record.id,
        "name": record.name,
        "mimeType": FOLDER_MIME if record.is_folder else record.mime_type,
        "modifiedTime": record.modified_at.isoformat(),
        "size": str(record.size) if record.size is not None else None,
    }


def list_files(session: Session, folder_id: Optional[str] = None) -> list[dict]:
    """Listet alle Dateien und Unterordner im angegebenen Ordner (None = Wurzel).

    Ordner erscheinen vor Dateien, danach neueste zuerst.
    """
    statement = (
        select(FileRecord)
        .where(FileRecord.parent_id == folder_id)
        .order_by(FileRecord.is_folder.desc(), FileRecord.modified_at.desc())
    )
    rows = session.exec(statement).all()
    return [_to_dict(r) for r in rows]


def create_folder(
    session: Session, name: str, parent_id: Optional[str] = None
) -> dict:
    """Erstellt einen neuen Ordner und gibt seine Metadaten zurück."""
    if parent_id is not None and not _is_folder(session, parent_id):
        raise RuntimeError("Zielordner existiert nicht.")

    record = FileRecord(name=name, parent_id=parent_id, is_folder=True)
    session.add(record)
    session.commit()
    session.refresh(record)
    return _to_dict(record)


def upload_file(
    session: Session,
    file_content: bytes,
    filename: str,
    mime_type: str,
    folder_id: Optional[str] = None,
) -> dict:
    """Speichert eine neue Datei lokal und legt ihren DB-Eintrag an.

    Gleichnamige Dateien werden NICHT überschrieben – es entsteht immer ein
    neuer Eintrag mit eigener ID.
    """
    if folder_id is not None and not _is_folder(session, folder_id):
        raise RuntimeError("Zielordner existiert nicht.")

    # Nur den Basisnamen speichern – nie einen Pfad (z. B. aus Ordner-Uploads).
    filename = os.path.basename((filename or "").replace("\\", "/")) or "Datei"

    _ensure_dir()
    record = FileRecord(
        name=filename,
        parent_id=folder_id,
        is_folder=False,
        mime_type=mime_type,
        size=len(file_content),
    )
    session.add(record)
    session.commit()
    session.refresh(record)

    with open(_blob_path(record.id), "wb") as f:
        f.write(file_content)

    return _to_dict(record)


def download_file(session: Session, file_id: str) -> tuple[bytes, str, str]:
    """Lädt eine Datei von der Platte. Gibt (Bytes, Dateiname, MIME-Type) zurück."""
    record = session.get(FileRecord, file_id)
    if record is None or record.is_folder:
        raise FileNotFoundError(f"Datei '{file_id}' nicht gefunden")

    path = _blob_path(file_id)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Datei-Inhalt für '{file_id}' nicht gefunden")

    with open(path, "rb") as f:
        content = f.read()
    return content, record.name, record.mime_type or "application/octet-stream"


def delete_file(session: Session, file_id: str) -> None:
    """Löscht eine Datei (Bytes + DB-Eintrag). Ordner werden ebenfalls entfernt."""
    record = session.get(FileRecord, file_id)
    if record is None:
        raise FileNotFoundError(f"Datei '{file_id}' nicht gefunden")

    path = _blob_path(file_id)
    if os.path.exists(path):
        os.remove(path)

    session.delete(record)
    session.commit()


def get_file_meta(session: Session, file_id: str) -> Optional[dict]:
    """Gibt die Metadaten einer Datei/eines Ordners zurück, oder None."""
    record = session.get(FileRecord, file_id)
    if record is None:
        return None
    return _to_dict(record)


def _is_folder(session: Session, file_id: str) -> bool:
    record = session.get(FileRecord, file_id)
    return record is not None and record.is_folder
