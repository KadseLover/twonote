from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from app.database import get_session
from app.models.user import User, UserCreate, UserRead, Token
from app.services.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_current_user_optional,
    get_user_by_username,
    hash_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def count_users(session: Session) -> int:
    """Zählt alle Nutzer in der Datenbank."""
    users = session.exec(select(User)).all()
    return len(users)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Registriert einen neuen Nutzer.
    - Erster Nutzer (keine Nutzer in DB): Offen für alle
    - Danach: Nur eingeloggte Nutzer können neue Nutzer anlegen
    """
    # Prüfen ob das der erste Nutzer ist
    is_first_user = count_users(session) == 0

    if not is_first_user:
        # Für weitere Nutzer: Auth erforderlich (wird über Dependency geprüft)
        # Da default=None oben, muss hier explizit geprüft werden
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nur eingeloggte Nutzer können neue Accounts anlegen",
            )

    # Username-Duplikat prüfen
    existing = get_user_by_username(session, user_data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{user_data.username}' ist bereits vergeben",
        )

    # Nutzer erstellen
    new_user = User(
        username=user_data.username,
        hashed_password=hash_password(user_data.password),
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user


@router.post("/register-auth", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_authenticated(
    user_data: UserCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Registriert einen neuen Nutzer (nur für eingeloggte Nutzer)."""
    existing = get_user_by_username(session, user_data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{user_data.username}' ist bereits vergeben",
        )

    new_user = User(
        username=user_data.username,
        hashed_password=hash_password(user_data.password),
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
):
    """Login mit Username und Passwort – gibt JWT Token zurück."""
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falscher Username oder Passwort",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token)


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    """Gibt den aktuell eingeloggten Nutzer zurück."""
    return current_user
