"""Vereinheitlichte Text-Beschaffung für KI-Funktionen (Datei oder Ordner).

Liefert den Grundtext, den Gemini sowohl für Zusammenfassungen als auch für das
Frage-Antwort-Feature braucht – egal ob es um ein einzelnes Dokument oder einen
ganzen (rekursiven) Ordner geht.
"""

from dataclasses import dataclass

from sqlmodel import Session

from app.services import storage as storage_service
from app.services import gemini as gemini_service

# Gleiche Grenze wie bei der Einzeldokument-Zusammenfassung
# (~4 Zeichen/Token → ca. 25.000 Token, gut im Free-Tier).
MAX_CHARS = 100_000


@dataclass
class ContextResult:
    text: str          # extrahierter (ggf. gekürzter) Grundtext
    name: str          # Datei- bzw. Ordnername
    file_count: int    # Anzahl tatsächlich einbezogener Dateien
    truncated: bool    # wurde der Text gekürzt?


def _truncate(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) > max_chars:
        return text[:max_chars], True
    return text, False


def extract_target_text(
    session: Session,
    target_kind: str,
    target_id: str,
    max_chars: int = MAX_CHARS,
) -> ContextResult:
    """Extrahiert den Text eines Ziels (``file`` oder ``folder``).

    Datei: lädt die Bytes und extrahiert den Text (PDF/Word).
    Ordner: sammelt rekursiv alle Dateien, extrahiert deren Text und fügt ihn –
    mit Datei-Überschriften getrennt – zusammen. Nicht extrahierbare Dateien
    (Bilder, Excel/PowerPoint, Bild-PDFs) werden übersprungen.
    """
    if target_kind == "file":
        content, filename, mime_type = storage_service.download_file(session, target_id)
        text = gemini_service.extract_text(content, mime_type)
        text, truncated = _truncate(text, max_chars)
        return ContextResult(text=text, name=filename, file_count=1, truncated=truncated)

    if target_kind == "folder":
        record = storage_service.get_file_meta(session, target_id)
        folder_name = record["name"] if record else "Ordner"

        records = storage_service.list_descendant_files(session, target_id)
        parts: list[str] = []
        file_count = 0
        for rec in records:
            try:
                content, filename, mime_type = storage_service.download_file(session, rec.id)
                file_text = gemini_service.extract_text(content, mime_type)
            except (ValueError, RuntimeError, FileNotFoundError):
                # Nicht unterstütztes Format oder fehlender Inhalt → überspringen
                continue
            if not file_text.strip():
                continue
            parts.append(f"\n\n===== Datei: {filename} =====\n\n{file_text}")
            file_count += 1

        combined = "".join(parts).strip()
        combined, truncated = _truncate(combined, max_chars)
        return ContextResult(
            text=combined, name=folder_name, file_count=file_count, truncated=truncated
        )

    raise ValueError(f"Unbekannter target_kind: {target_kind}")
