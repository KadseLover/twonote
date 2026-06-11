import os
from sqlmodel import SQLModel, Session, create_engine

# SQLite-Datenbankdatei im /app/data Verzeichnis (Docker Volume)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/twonote.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Für SQLite + FastAPI notwendig
    echo=False,
)


def create_db_and_tables() -> None:
    """Erstellt alle Tabellen falls sie nicht existieren."""
    os.makedirs("data", exist_ok=True)
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI Dependency für eine Datenbank-Session."""
    with Session(engine) as session:
        yield session
