from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from app.database import get_session
from app.models.user import User
from app.models.usage import AiUsage  # noqa: F401  (Tabelle registrieren)
from app.models.summary import Summary  # noqa: F401  (Tabelle registrieren)
from app.models.chat import ChatSession, ChatMessage  # noqa: F401  (Tabellen registrieren)
from app.services import storage as storage_service
from app.services import gemini as gemini_service
from app.services import usage as usage_service
from app.services import summaries as summaries_service
from app.services import ai_context as ai_context_service
from app.services import chat as chat_service
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/files", tags=["ai"])


class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    target_kind: str = "file"  # "file" | "folder"


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


@router.post("/{folder_id}/summarize-folder", summary="Ganzen Ordner mit Gemini AI zusammenfassen")
def summarize_folder(
    folder_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Fasst alle Dateien eines Ordners (rekursiv inkl. Unterordner) zusammen.

    Sammelt den Text aller unterstützten Dateien, erstellt eine zusammenhängende
    Markdown-Zusammenfassung mit Gemini und speichert sie wie eine Dokument-
    Zusammenfassung (Schlüssel = Ordner-ID).
    """
    meta = storage_service.get_file_meta(session, folder_id)
    if not meta or meta["mimeType"] != storage_service.FOLDER_MIME:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ordner '{folder_id}' nicht gefunden",
        )
    folder_name = meta["name"]

    try:
        ctx = ai_context_service.extract_target_text(session, "folder", folder_id)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    # Keine verwertbaren Dateien → freundliche Meldung (kein Gemini-Aufruf, keine Zählung)
    if ctx.file_count == 0 or not ctx.text.strip():
        return {
            "file_id": folder_id,
            "filename": folder_name,
            "summary": (
                "## ⚠️ Kein Text gefunden\n\n"
                "Dieser Ordner enthält keine Dateien mit extrahierbarem Text "
                "(unterstützt werden PDF und Word). Unterordner werden mit einbezogen."
            ),
        }

    try:
        summary = gemini_service.summarize_folder(ctx.text, folder_name, ctx.truncated)
    except gemini_service.RateLimitError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    usage_service.record_summary(session)
    summaries_service.save_summary(session, folder_id, folder_name, summary)

    return {
        "file_id": folder_id,
        "filename": folder_name,
        "summary": summary,
    }


def _serialize_messages(messages: list[ChatMessage]) -> list[dict]:
    return [
        {"role": m.role, "content": m.content, "created_at": m.created_at}
        for m in messages
    ]


@router.get("/{target_id}/chat", summary="Neueste Frage-Antwort-Unterhaltung eines Ziels")
def latest_chat(
    target_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Gibt die zuletzt genutzte Unterhaltung des Nutzers für dieses Ziel zurück (oder null)."""
    chat_session = chat_service.get_latest_session_for_target(session, target_id, current_user.id)
    if chat_session is None:
        return None
    messages = chat_service.get_messages(session, chat_session.id)
    return {
        "session_id": chat_session.id,
        "target_kind": chat_session.target_kind,
        "target_name": chat_session.target_name,
        "messages": _serialize_messages(messages),
    }


@router.post("/{target_id}/chat", summary="Frage zu einem Dokument/Ordner stellen (mit Rückfragen)")
def chat(
    target_id: str,
    body: ChatRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Beantwortet eine Frage zu einem Dokument oder Ordner.

    Ohne ``session_id`` wird eine neue Unterhaltung gestartet (der Grundtext wird
    einmalig extrahiert und gespeichert). Mit ``session_id`` wird die bestehende
    Unterhaltung fortgesetzt – so beziehen sich Rückfragen auf vorherige Antworten.
    """
    question = body.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Die Frage darf nicht leer sein.",
        )

    if body.session_id:
        chat_session = chat_service.get_session_for_user(session, body.session_id, current_user.id)
        if chat_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unterhaltung nicht gefunden.",
            )
        context_text = chat_session.context_text
        target_name = chat_session.target_name
        history = [(m.role, m.content) for m in chat_service.get_messages(session, chat_session.id)]
    else:
        try:
            ctx = ai_context_service.extract_target_text(session, body.target_kind, target_id)
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ziel '{target_id}' nicht gefunden",
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
        if not ctx.text.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Kein durchsuchbarer Text gefunden (unterstützt: PDF, Word).",
            )
        chat_session = None  # erst nach erfolgreicher Antwort anlegen
        context_text = ctx.text
        target_name = ctx.name
        history = []

    try:
        answer = gemini_service.answer_question(context_text, target_name, history, question)
    except gemini_service.RateLimitError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    if chat_session is None:
        chat_session = chat_service.create_session(
            session,
            user_id=current_user.id,
            target_kind=body.target_kind,
            target_id=target_id,
            target_name=target_name,
            context_text=context_text,
        )

    chat_service.add_message(session, chat_session.id, "user", question)
    chat_service.add_message(session, chat_session.id, "assistant", answer)
    chat_service.touch(session, chat_session)
    usage_service.record_summary(session)

    messages = chat_service.get_messages(session, chat_session.id)
    return {
        "session_id": chat_session.id,
        "answer": answer,
        "messages": _serialize_messages(messages),
    }
