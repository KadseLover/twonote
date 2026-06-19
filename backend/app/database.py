import os
from sqlalchemy import text
from sqlmodel import SQLModel, Session, create_engine

# SQLite-Datenbankdatei im /app/data Verzeichnis (Docker Volume)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/twonote.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Für SQLite + FastAPI notwendig
    echo=False,
)


def create_db_and_tables() -> None:
    """Erstellt fehlende Tabellen und führt leichte Bereinigungen/Migrationen aus."""
    os.makedirs("data", exist_ok=True)
    SQLModel.metadata.create_all(engine)
    _drop_annotation_table()
    _ensure_filerecord_names()
    _add_avatar_columns()


def _drop_annotation_table() -> None:
    """Entfernt die alte ``annotation``-Tabelle (idempotent).

    Das PDF-Notizen-/Versionssystem wurde zugunsten der OnlyOffice-Bearbeitung
    ausgebaut – die Tabelle samt gespeicherter Fabric-Annotationen wird nicht
    mehr benötigt.
    """
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS annotation"))
        conn.commit()


def _ensure_filerecord_names() -> None:
    """Bereinigt Datei-/Ordnernamen, die noch einen Pfad enthalten (idempotent).

    Aus der früheren Drive-Datenbasis übernommene Dateien hatten teils den Pfad im
    Namen (z. B. ``09_Vollmachten/04_Übung.pdf``). Hier auf den reinen Basisnamen
    kürzen. Nach dem ersten Lauf gibt es keine Namen mehr mit Trenner → No-Op.
    """
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='filerecord'")
        ).first()
        if not exists:
            return
        # char(92) = Backslash – über instr() ohne LIKE-Escaping suchen.
        rows = conn.execute(
            text("SELECT id, name FROM filerecord WHERE instr(name, '/') > 0 OR instr(name, char(92)) > 0")
        ).fetchall()
        for row_id, name in rows:
            base = name.replace("\\", "/").rsplit("/", 1)[-1] or name
            conn.execute(
                text("UPDATE filerecord SET name = :n WHERE id = :id"),
                {"n": base, "id": row_id},
            )
        conn.commit()


def _add_avatar_columns() -> None:
    """Ergänzt die Avatar-Spalten in der ``user``-Tabelle (idempotent).

    ``create_all`` legt bei bestehenden Tabellen keine neuen Spalten an, daher
    hier per ``ALTER TABLE`` nachrüsten, falls sie fehlen.
    """
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='user'")
        ).first()
        if not exists:
            return
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(user)")).fetchall()}
        if "has_avatar" not in cols:
            conn.execute(text("ALTER TABLE user ADD COLUMN has_avatar BOOLEAN DEFAULT 0"))
        if "avatar_ext" not in cols:
            conn.execute(text("ALTER TABLE user ADD COLUMN avatar_ext TEXT"))
        conn.commit()


def get_session():
    """FastAPI Dependency für eine Datenbank-Session."""
    with Session(engine) as session:
        yield session
