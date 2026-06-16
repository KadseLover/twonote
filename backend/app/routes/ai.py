from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.database import get_session
from app.models.user import User
from app.models.usage import AiUsage  # noqa: F401  (Tabelle registrieren)
from app.models.summary import Summary  # noqa: F401  (Tabelle registrieren)
from app.services import storage as storage_service
from app.services import gemini as gemini_service
from app.services import usage as usage_service
from app.services import summaries as summaries_service
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/files", tags=["ai"])


@router.get("/ai-usage", summary="Heutigen Gemini-Verbrauch abrufen")
def ai_usage(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Gibt verbrauchte/erlaubte Gemini-Anfragen für den heutigen Tag zurück."""
    return usage_service.get_usage(session)


@router.get("/summaries", summary="Alle gespeicherten Zusammenfassungen (Archiv)")
def list_summaries(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Globales Archiv: alle Zusammenfassungen über alle Dokumente, neueste zuerst."""
    return summaries_service.get_all(session)


@router.get("/{file_id}/summary", summary="Neueste gespeicherte Zusammenfassung einer Datei")
def latest_summary(
    file_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Gibt die zuletzt gespeicherte Zusammenfassung der Datei zurück (oder null)."""
    row = summaries_service.get_latest_for_file(session, file_id)
    if row is None:
        return None
    return {
        "content": row.content,
        "filename": row.filename,
        "created_at": row.created_at,
    }


@router.post("/{file_id}/summarize", summary="Dokument mit Gemini AI zusammenfassen")
def summarize_document(
    file_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Lädt eine Datei lokal, extrahiert den Text und erstellt
    eine strukturierte Zusammenfassung mit Google Gemini AI.

    Unterstützt: PDF, Word (.docx)
    Gibt eine Markdown-formatierte Zusammenfassung zurück.
    """
    # Datei lokal laden
    try:
        content, filename, mime_type = storage_service.download_file(session, file_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datei '{file_id}' nicht gefunden",
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )

    # Zusammenfassung erstellen
    try:
        summary = gemini_service.summarize_document(content, filename, mime_type)
    except gemini_service.RateLimitError as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    # Erfolgreiche Anfrage für die Tagesstatistik zählen
    usage_service.record_summary(session)
    # Zusammenfassung im Verlauf/Archiv speichern
    summaries_service.save_summary(session, file_id, filename, summary)

    return {
        "file_id": file_id,
        "filename": filename,
        "summary": summary,
    }
