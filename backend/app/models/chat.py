from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlmodel import Field, SQLModel


class ChatSession(SQLModel, table=True):
    """Eine Frage-Antwort-Unterhaltung zu einem Dokument oder Ordner.

    Der ``context_text`` (der einmal extrahierte, gekürzte Grundtext des Ziels)
    wird beim Anlegen der Session gespeichert, damit Rückfragen den Ordner nicht
    bei jeder Anfrage erneut rekursiv einlesen müssen.
    """

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    user_id: int = Field(index=True)               # Eigentümer (User.id)
    target_kind: str                               # "file" | "folder"
    target_id: str = Field(index=True)             # FileRecord.id
    target_name: str                               # Name zum Zeitpunkt der Erstellung
    context_text: str                              # extrahierter, gekürzter Grundtext
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatMessage(SQLModel, table=True):
    """Eine einzelne Nachricht innerhalb einer ``ChatSession``."""

    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    session_id: str = Field(index=True)            # ChatSession.id
    role: str                                      # "user" | "assistant"
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
