import io

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from app.config import settings


class RateLimitError(RuntimeError):
    """Gemini hat die Anfrage wegen Rate-Limits abgelehnt (Free-Tier-Kontingent erschöpft)."""

# Modell konfigurieren (einmal beim Import)
genai.configure(api_key=settings.gemini_api_key)

# gemini-2.5-flash: Kostenloses Tier, aktuelles Flash-Modell
MODEL_NAME = "gemini-2.5-flash"

SUMMARY_PROMPT_TEMPLATE = """Du bist ein hilfreicher Lernassistent. Analysiere das folgende Dokument und erstelle eine strukturierte Zusammenfassung auf Deutsch.

Dokument: "{filename}"

Inhalt:
{text}

---

Bitte erstelle eine Zusammenfassung mit folgender Struktur:

## 📋 Kurzzusammenfassung
Eine kompakte Übersicht des Dokuments in 2-3 Sätzen.

## 🔑 Schlüsselbegriffe
Die wichtigsten Begriffe und Konzepte als Liste.

## 📌 Hauptpunkte
Die wesentlichen Aussagen und Inhalte als übersichtliche Liste.

## 💡 Lernhinweise
Besonders wichtige oder schwierige Konzepte, die besondere Aufmerksamkeit verdienen.
"""


def extract_text_from_pdf(content: bytes) -> str:
    """Extrahiert Text aus einem PDF mit pypdf."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n\n".join(text_parts)
    except Exception as e:
        raise RuntimeError(f"Fehler beim Lesen der PDF-Datei: {e}")


def extract_text_from_docx(content: bytes) -> str:
    """Extrahiert Text aus einem Word-Dokument (.docx)."""
    try:
        from docx import Document

        doc = Document(io.BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except Exception as e:
        raise RuntimeError(f"Fehler beim Lesen der Word-Datei: {e}")


def extract_text(content: bytes, mime_type: str) -> str:
    """Extrahiert Text je nach Dateiformat."""
    if mime_type == "application/pdf":
        return extract_text_from_pdf(content)
    elif mime_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ):
        return extract_text_from_docx(content)
    else:
        raise ValueError(f"Nicht unterstützter MIME-Type für Textextraktion: {mime_type}")


def summarize_document(content: bytes, filename: str, mime_type: str) -> str:
    """
    Erstellt eine strukturierte Zusammenfassung eines Dokuments mit Gemini AI.

    Args:
        content: Datei-Inhalt als bytes
        filename: Dateiname (für den Prompt)
        mime_type: MIME-Type der Datei

    Returns:
        Markdown-formatierte Zusammenfassung als String
    """
    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY nicht konfiguriert. Bitte in .env setzen."
        )

    # Text extrahieren
    text = extract_text(content, mime_type)

    if not text.strip():
        return (
            "## ⚠️ Kein Text gefunden\n\n"
            "Das Dokument enthält keinen extrahierbaren Text. "
            "Möglicherweise handelt es sich um ein eingescanntes Dokument (Bild-PDF)."
        )

    # Text auf ~100.000 Zeichen kürzen um API-Limits zu respektieren
    # (bei ~4 Zeichen/Token = ca. 25.000 Token, gut im Free-Tier)
    max_chars = 100_000
    truncated = False
    if len(text) > max_chars:
        text = text[:max_chars]
        truncated = True

    prompt = SUMMARY_PROMPT_TEMPLATE.format(filename=filename, text=text)

    model = genai.GenerativeModel(MODEL_NAME)
    try:
        response = model.generate_content(prompt)
    except google_exceptions.ResourceExhausted as e:
        raise RateLimitError(
            "Das tägliche Gemini-Free-Tier-Kontingent ist erschöpft. "
            "Bitte später erneut versuchen (Reset täglich um Mitternacht Pacific Time)."
        ) from e
    except google_exceptions.GoogleAPIError as e:
        raise RuntimeError(f"Gemini-API-Fehler: {e}") from e

    result = response.text

    if truncated:
        result += (
            "\n\n---\n> ⚠️ **Hinweis:** Das Dokument wurde für die Zusammenfassung "
            "auf die ersten 100.000 Zeichen gekürzt."
        )

    return result
