from typing import Optional

from sqlmodel import Session, select

from app.models.summary import Summary


def save_summary(session: Session, file_id: str, filename: str, content: str) -> Summary:
    """Speichert eine neue Zusammenfassung (Verlauf – überschreibt nichts)."""
    row = Summary(file_id=file_id, filename=filename, content=content)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_latest_for_file(session: Session, file_id: str) -> Optional[Summary]:
    """Gibt die zuletzt gespeicherte Zusammenfassung einer Datei zurück (oder None)."""
    statement = (
        select(Summary)
        .where(Summary.file_id == file_id)
        .order_by(Summary.created_at.desc())
    )
    return session.exec(statement).first()


def get_all(session: Session) -> list[Summary]:
    """Gibt alle gespeicherten Zusammenfassungen zurück, neueste zuerst."""
    statement = select(Summary).order_by(Summary.created_at.desc())
    return list(session.exec(statement).all())
