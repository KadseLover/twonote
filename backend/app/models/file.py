from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlmodel import Field, SQLModel


class FileRecord(SQLModel, table=True):
    """Eine lokal gespeicherte Datei oder ein Ordner.

    Die eigentlichen Datei-Bytes liegen unter ``data/files/{id}`` auf der
    Server-Platte (Docker-Volume). Ordner haben keine Bytes (``is_folder=True``).

    Die ``id`` wird als opaker String behandelt: neue Dateien/Ordner bekommen
    eine uuid4-Hex-ID, aus Google Drive migrierte Einträge behalten ihre
    ursprüngliche Drive-ID – so bleibt bestehende ``Summary.file_id`` ohne
    Umschlüsselung gültig.
    """

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    name: str
    parent_id: Optional[str] = Field(default=None, index=True)  # None = Wurzel
    is_folder: bool = False
    mime_type: str = ""
    size: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
