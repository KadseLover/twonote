from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlmodel import Session

from app.config import settings
from app.models.usage import AiUsage

# Gemini-Kontingente werden täglich um Mitternacht Pacific Time zurückgesetzt.
PACIFIC = ZoneInfo("America/Los_Angeles")


def _today_pt() -> str:
    """Aktuelles Datum in Pacific Time als ISO-String (YYYY-MM-DD)."""
    return datetime.now(PACIFIC).date().isoformat()


def record_summary(session: Session) -> None:
    """Zählt eine erfolgreiche Gemini-Anfrage für den heutigen (PT-)Tag."""
    today = _today_pt()
    row = session.get(AiUsage, today)
    if row is None:
        row = AiUsage(usage_date=today, count=0)
    row.count += 1
    session.add(row)
    session.commit()


def _next_reset_utc() -> str:
    """Nächste Mitternacht Pacific Time als UTC-ISO-String (Zeitpunkt des Resets)."""
    now_pt = datetime.now(PACIFIC)
    next_midnight = (now_pt + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return next_midnight.astimezone(timezone.utc).isoformat()


def get_usage(session: Session) -> dict:
    """Liefert Verbrauch und Limit für den heutigen (PT-)Tag."""
    today = _today_pt()
    row = session.get(AiUsage, today)
    return {
        "used": row.count if row else 0,
        "limit": settings.gemini_daily_limit,
        "date": today,
        "resets_at": _next_reset_utc(),
    }
