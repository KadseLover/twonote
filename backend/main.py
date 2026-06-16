from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import create_db_and_tables
from app.routes import auth, files, ai


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startet und beendet den Server sauber."""
    # Beim Start: Datenbank-Tabellen anlegen
    create_db_and_tables()
    print("Datenbank bereit")
    yield
    # Beim Beenden: nichts zu tun


app = FastAPI(
    title="TwoNote API",
    description=(
        "Backend für TwoNote – Dokumente lokal verwalten, "
        "PDFs bearbeiten und mit Gemini AI zusammenfassen."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS konfigurieren
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Interner Serverfehler: {exc}"},
    )


# Router registrieren
app.include_router(auth.router)
app.include_router(files.router)
app.include_router(ai.router)


@app.get("/", tags=["root"])
def root():
    return {
        "message": "TwoNote API läuft",
        "docs": "/docs",
        "version": "1.0.0",
    }


@app.get("/health", tags=["root"])
def health():
    return {"status": "ok"}
