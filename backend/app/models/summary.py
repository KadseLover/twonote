from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class Summary(SQLModel, table=True):
    """Gespeicherte KI-Zusammenfassung (voller Verlauf, eine Zeile pro Erstellung)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    file_id: str = Field(index=True)          # lokale Datei-ID (FileRecord.id)
    filename: str                              # Dateiname zum Zeitpunkt der Erstellung
    content: str                               # Markdown-Zusammenfassung
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
