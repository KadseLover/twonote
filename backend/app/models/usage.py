from sqlmodel import Field, SQLModel


class AiUsage(SQLModel, table=True):
    """Tägliche Zählung der Gemini-Anfragen.

    Pro Tag (Pacific Time, wie Googles Reset) eine Zeile. Eine neue Datums-Zeile
    entspricht dem täglichen Reset – alte Zeilen bleiben als Historie erhalten.
    """
    usage_date: str = Field(primary_key=True)  # ISO-Datum (YYYY-MM-DD) in Pacific Time
    count: int = Field(default=0)
