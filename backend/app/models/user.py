from typing import Optional
from sqlmodel import Field, SQLModel


class UserBase(SQLModel):
    username: str = Field(index=True, unique=True, min_length=3, max_length=50)


class User(UserBase, table=True):
    """Datenbank-Tabelle für Nutzer."""
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    is_active: bool = Field(default=True)


class UserCreate(UserBase):
    """Schema für die Registrierung."""
    password: str = Field(min_length=6)


class UserRead(UserBase):
    """Schema für die API-Antwort (ohne Passwort)."""
    id: int
    is_active: bool


class Token(SQLModel):
    """JWT Token Antwort."""
    access_token: str
    token_type: str = "bearer"


class TokenData(SQLModel):
    """Daten aus dem dekodierten JWT Token."""
    username: Optional[str] = None
