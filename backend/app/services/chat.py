"""DB-Helfer für persistierte Frage-Antwort-Unterhaltungen (ChatSession/ChatMessage)."""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from app.models.chat import ChatSession, ChatMessage


def create_session(
    session: Session,
    user_id: int,
    target_kind: str,
    target_id: str,
    target_name: str,
    context_text: str,
) -> ChatSession:
    """Legt eine neue Chat-Session an und speichert den Grundtext einmalig."""
    row = ChatSession(
        user_id=user_id,
        target_kind=target_kind,
        target_id=target_id,
        target_name=target_name,
        context_text=context_text,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_session_for_user(
    session: Session, session_id: str, user_id: int
) -> Optional[ChatSession]:
    """Lädt eine Chat-Session, aber nur wenn sie dem Nutzer gehört (sonst None)."""
    row = session.get(ChatSession, session_id)
    if row is None or row.user_id != user_id:
        return None
    return row


def get_latest_session_for_target(
    session: Session, target_id: str, user_id: int
) -> Optional[ChatSession]:
    """Neueste Chat-Session eines Nutzers für ein bestimmtes Ziel (oder None)."""
    statement = (
        select(ChatSession)
        .where(ChatSession.target_id == target_id)
        .where(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc())
    )
    return session.exec(statement).first()


def add_message(session: Session, session_id: str, role: str, content: str) -> ChatMessage:
    """Hängt eine Nachricht an eine Session an."""
    row = ChatMessage(session_id=session_id, role=role, content=content)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_messages(session: Session, session_id: str) -> list[ChatMessage]:
    """Alle Nachrichten einer Session in chronologischer Reihenfolge."""
    statement = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    return list(session.exec(statement).all())


def touch(session: Session, chat_session: ChatSession) -> None:
    """Aktualisiert ``updated_at`` der Session (nach neuer Aktivität)."""
    chat_session.updated_at = datetime.now(timezone.utc)
    session.add(chat_session)
    session.commit()
