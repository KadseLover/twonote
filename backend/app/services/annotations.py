from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session, select

from app.models.annotation import Annotation


def list_for_file(session: Session, file_id: str) -> list[Annotation]:
    """Gibt alle Notiz-Stände einer Datei zurück, neueste zuerst."""
    statement = (
        select(Annotation)
        .where(Annotation.file_id == file_id)
        .order_by(Annotation.updated_at.desc())
    )
    return list(session.exec(statement).all())


def get_latest(session: Session, file_id: str) -> Optional[Annotation]:
    """Gibt den zuletzt aktualisierten Stand einer Datei zurück (oder None)."""
    statement = (
        select(Annotation)
        .where(Annotation.file_id == file_id)
        .order_by(Annotation.updated_at.desc())
    )
    return session.exec(statement).first()


def get_version(session: Session, version_id: int) -> Optional[Annotation]:
    """Gibt einen bestimmten Stand zurück (oder None)."""
    return session.get(Annotation, version_id)


def create_version(session: Session, file_id: str, data: str, label: str = "") -> Annotation:
    """Legt einen neuen, eigenständigen Notiz-Stand an."""
    row = Annotation(file_id=file_id, data=data, label=label)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def update_version(session: Session, version_id: int, data: str) -> Optional[Annotation]:
    """Überschreibt einen bestehenden Stand. Gibt None zurück, wenn nicht gefunden."""
    row = session.get(Annotation, version_id)
    if row is None:
        return None
    row.data = data
    row.updated_at = datetime.now(timezone.utc)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row
