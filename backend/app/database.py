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

# Leichte Migrationen: SQLite ergänzt fehlende Spalten in bestehenden Tabellen
# nicht automatisch (create_all legt nur fehlende Tabellen an). Hier listen wir
# Spalten, die nachträglich hinzugekommen sind: {Tabelle: {Spalte: SQL-Definition}}.
_COLUMN_MIGRATIONS: dict[str, dict[str, str]] = {
    "annotation": {
        "label": "VARCHAR NOT NULL DEFAULT ''",
        # SQLite erlaubt bei ADD COLUMN keinen dynamischen Default (now()), daher
        # nullable hinzufügen und unten aus updated_at nachfüllen.
        "created_at": "DATETIME",
    },
}


def create_db_and_tables() -> None:
    """Erstellt alle Tabellen falls sie nicht existieren und ergänzt neue Spalten."""
    os.makedirs("data", exist_ok=True)
    SQLModel.metadata.create_all(engine)
    _ensure_columns()
    _ensure_indexes()
    _ensure_filerecord_names()


def _ensure_columns() -> None:
    """Fügt in bestehenden Tabellen fehlende Spalten hinzu (idempotent, nur SQLite)."""
    with engine.connect() as conn:
        for table, columns in _COLUMN_MIGRATIONS.items():
            existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            if not existing:
                continue  # Tabelle existiert (noch) nicht – wurde von create_all angelegt
            for column, definition in columns.items():
                if column not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
        # Backfill: Alt-Annotationen ohne created_at erben ihren updated_at-Wert.
        ann_cols = {row[1] for row in conn.execute(text("PRAGMA table_info(annotation)"))}
        if {"created_at", "updated_at"} <= ann_cols:
            conn.execute(
                text("UPDATE annotation SET created_at = updated_at WHERE created_at IS NULL")
            )
        conn.commit()


def _ensure_indexes() -> None:
    """Korrigiert veraltete Index-Definitionen (idempotent, nur SQLite).

    Ein früheres Schema legte annotation.file_id als UNIQUE-Index an (eine
    Annotation pro Datei). Das aktuelle Modell erlaubt mehrere Versionen pro
    Datei (Field(index=True), nicht-unique). create_all ändert bestehende
    Indizes nicht – daher hier den Unique-Index droppen und nicht-unique neu
    anlegen (Name beibehalten).
    """
    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA index_list(annotation)")).fetchall()
        for _seq, name, unique, *_rest in rows:
            if name == "ix_annotation_file_id" and unique:
                conn.execute(text("DROP INDEX ix_annotation_file_id"))
                conn.execute(text("CREATE INDEX ix_annotation_file_id ON annotation (file_id)"))
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


def get_session():
    """FastAPI Dependency für eine Datenbank-Session."""
    with Session(engine) as session:
        yield session
