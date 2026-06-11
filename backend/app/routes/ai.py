from fastapi import APIRouter, Depends, HTTPException, status

from app.models.user import User
from app.services import drive as drive_service
from app.services import gemini as gemini_service
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/files", tags=["ai"])


@router.post("/{file_id}/summarize", summary="Dokument mit Gemini AI zusammenfassen")
def summarize_document(
    file_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Lädt eine Datei aus Drive, extrahiert den Text und erstellt
    eine strukturierte Zusammenfassung mit Google Gemini AI.

    Unterstützt: PDF, Word (.docx)
    Gibt eine Markdown-formatierte Zusammenfassung zurück.
    """
    # Datei aus Drive laden
    try:
        content, filename, mime_type = drive_service.download_file(file_id)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Google Drive Fehler: {e}",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Datei '{file_id}' nicht gefunden",
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

    return {
        "file_id": file_id,
        "filename": filename,
        "summary": summary,
    }
