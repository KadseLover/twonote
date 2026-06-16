from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class Annotation(SQLModel, table=True):
    """Ein eigenständiger, bearbeitbarer Notiz-Stand eines PDFs (fabric.js-Canvas als JSON).

    Pro Datei kann es mehrere Versionen geben – beim Speichern entscheidet der
    Nutzer, ob er den geladenen Stand überschreibt oder einen neuen Stand anlegt.
    Das Original-PDF bleibt unverändert; Texte/Markierungen bleiben editierbar.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    file_id: str = Field(index=True)  # lokale Datei-ID (FileRecord.id)
    label: str = ""                    # selbst vergebener Versionsname
    data: str                          # fabric-Canvas als JSON
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
