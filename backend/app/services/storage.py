"""Lokale Datei-Speicherung auf der Server-Platte (ersetzt Google Drive).

Datei-Metadaten (Name, Ordner-Hierarchie, Größe …) liegen in der ``file``-Tabelle
(`app.models.file.FileRecord`), die rohen Bytes flach unter ``data/files/{id}``.
Ordner sind reine DB-Einträge ohne Bytes.
"""

import os
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from app.models.file import FileRecord

# MIME-Type, an dem das Frontend Ordner erkennt.
FOLDER_MIME = "application/vnd.twonote.folder"

# Dateiendung → (OnlyOffice documentType, fileType, editierbar?).
# Legacy-Binärformate (.doc/.xls/.ppt) lassen sich nicht direkt co-editieren → nur Ansicht.
_EDITOR_MAP: dict[str, tuple[str, bool]] = {
    "pdf": ("pdf", True),
    "docx": ("word", True),
    "doc": ("word", False),
    "xlsx": ("cell", True),
    "xls": ("cell", False),
    "pptx": ("slide", True),
    "ppt": ("slide", False),
}


def editor_meta(filename: str) -> tuple[str, str, bool]:
    """Bestimmt (documentType, fileType, editierbar) für den OnlyOffice-Editor.

    ``fileType`` ist die reine Endung (z. B. ``docx``); ``documentType`` die
    OnlyOffice-Kategorie (``word``/``cell``/``slide``/``pdf``). Unbekannte
    Endungen werden als nicht-editierbares Word-Dokument behandelt.
    """
    ext = os.path.splitext(filename or "")[1].lstrip(".").lower()
    document_type, editable = _EDITOR_MAP.get(ext, ("word", False))
    return document_type, ext, editable

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


def list_descendant_files(session: Session, folder_id: str) -> list[FileRecord]:
    """Sammelt alle Dateien (keine Ordner) unterhalb eines Ordners – rekursiv.

    Läuft den ``parent_id``-Baum iterativ über eine Queue ab, sodass auch tief
    verschachtelte Unterordner berücksichtigt werden. Reihenfolge: neueste zuerst,
    Ordnerebene für Ordnerebene.
    """
    files: list[FileRecord] = []
    queue: list[str] = [folder_id]
    seen: set[str] = set()
    while queue:
        current = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        statement = (
            select(FileRecord)
            .where(FileRecord.parent_id == current)
            .order_by(FileRecord.is_folder.desc(), FileRecord.modified_at.desc())
        )
        for record in session.exec(statement).all():
            if record.is_folder:
                queue.append(record.id)
            else:
                files.append(record)
    return files


def _collect_descendants(session: Session, folder_id: str) -> list[FileRecord]:
    """Sammelt alle Nachfahren eines Ordners – Dateien **und** Unterordner – rekursiv."""
    descendants: list[FileRecord] = []
    queue: list[str] = [folder_id]
    seen: set[str] = set()
    while queue:
        current = queue.pop(0)
        if current in seen:
            continue
        seen.add(current)
        statement = select(FileRecord).where(FileRecord.parent_id == current)
        for record in session.exec(statement).all():
            descendants.append(record)
            if record.is_folder:
                queue.append(record.id)
    return descendants


def _is_ancestor(session: Session, ancestor_id: str, node_id: Optional[str]) -> bool:
    """Prüft, ob ``ancestor_id`` ein Vorfahre von ``node_id`` ist (über ``parent_id``)."""
    current = node_id
    seen: set[str] = set()
    while current is not None and current not in seen:
        if current == ancestor_id:
            return True
        seen.add(current)
        record = session.get(FileRecord, current)
        current = record.parent_id if record else None
    return False


def move_file(session: Session, file_id: str, new_parent_id: Optional[str]) -> None:
    """Verschiebt eine Datei/einen Ordner in einen anderen Ordner (``None`` = Wurzel).

    Wirft ``RuntimeError`` bei ungültigem Ziel oder wenn dadurch ein Zyklus
    entstünde (Ordner in sich selbst oder einen seiner Unterordner). Committet
    NICHT – der Aufrufer committet (für atomare Mehrfach-Verschiebungen).
    """
    record = session.get(FileRecord, file_id)
    if record is None:
        raise RuntimeError(f"Eintrag '{file_id}' nicht gefunden.")

    if new_parent_id == file_id:
        raise RuntimeError("Ein Eintrag kann nicht in sich selbst verschoben werden.")

    if new_parent_id is not None:
        target = session.get(FileRecord, new_parent_id)
        if target is None or not target.is_folder:
            raise RuntimeError("Zielordner existiert nicht.")
        # Ordner darf nicht in einen seiner eigenen Nachfahren wandern.
        if record.is_folder and _is_ancestor(session, file_id, new_parent_id):
            raise RuntimeError("Ein Ordner kann nicht in sich selbst verschoben werden.")

    record.parent_id = new_parent_id
    session.add(record)


def collect_for_zip(session: Session, ids: list[str]) -> list[tuple[str, str]]:
    """Liefert ``(arcname, file_id)``-Paare für ein ZIP über die gegebene Auswahl.

    Dateien werden mit ihrem Namen aufgenommen, Ordner rekursiv mit erhaltener
    Struktur (``Ordnername/Unterordner/Datei``). Leere Ordner entfallen.
    """
    entries: list[tuple[str, str]] = []

    def add_folder(folder: FileRecord, prefix: str) -> None:
        base = f"{prefix}{folder.name}/"
        children = session.exec(
            select(FileRecord).where(FileRecord.parent_id == folder.id)
        ).all()
        for child in children:
            if child.is_folder:
                add_folder(child, base)
            else:
                entries.append((f"{base}{child.name}", child.id))

    for file_id in ids:
        record = session.get(FileRecord, file_id)
        if record is None:
            continue
        if record.is_folder:
            add_folder(record, "")
        else:
            entries.append((record.name, record.id))
    return entries


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


def save_content(session: Session, file_id: str, content: bytes) -> None:
    """Überschreibt die Bytes einer bestehenden Datei (für OnlyOffice-Callbacks).

    Aktualisiert Größe und ``modified_at``; der ``modified_at``-Wert fließt in den
    OnlyOffice-document.key ein, sodass beim nächsten Öffnen der neue Stand geladen wird.
    """
    record = session.get(FileRecord, file_id)
    if record is None or record.is_folder:
        raise FileNotFoundError(f"Datei '{file_id}' nicht gefunden")

    _ensure_dir()
    with open(_blob_path(file_id), "wb") as f:
        f.write(content)

    record.size = len(content)
    record.modified_at = datetime.now(timezone.utc)
    session.add(record)
    session.commit()


def delete_file(session: Session, file_id: str) -> None:
    """Löscht eine Datei oder einen Ordner.

    Ordner werden **rekursiv** entfernt: alle enthaltenen Dateien/Unterordner
    samt ihrer Bytes auf der Platte werden gelöscht. So bleiben keine verwaisten
    Einträge oder Blob-Reste zurück.
    """
    record = session.get(FileRecord, file_id)
    if record is None:
        raise FileNotFoundError(f"Datei '{file_id}' nicht gefunden")

    # Bei Ordnern zuerst alle Nachfahren einsammeln und entfernen.
    if record.is_folder:
        for descendant in _collect_descendants(session, file_id):
            if not descendant.is_folder:
                blob = _blob_path(descendant.id)
                if os.path.exists(blob):
                    os.remove(blob)
            session.delete(descendant)
    else:
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
