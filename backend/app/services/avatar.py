"""Lokale Avatar-Speicherung – spiegelt das Blob-Muster aus ``storage.py``.

Profilbilder liegen flach unter ``data/avatars/{user_id}.{ext}``. Die Metadaten
(``has_avatar``/``avatar_ext``) stehen in der ``user``-Tabelle.
"""

import os

AVATARS_DIR = os.path.join("data", "avatars")

# Unterstützte Bildformate (MIME-Type → Endung).
EXT_BY_MIME = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}
_ALL_EXTS = ("jpg", "png", "webp", "gif")


def _avatar_path(user_id: int, ext: str) -> str:
    return os.path.join(AVATARS_DIR, f"{user_id}.{ext}")


def _ensure_dir() -> None:
    os.makedirs(AVATARS_DIR, exist_ok=True)


def save_avatar(user_id: int, content: bytes, ext: str) -> None:
    """Speichert das Profilbild eines Nutzers (überschreibt ein vorhandenes)."""
    _ensure_dir()
    # Evtl. vorhandenes Bild in anderem Format zuerst entfernen.
    for old_ext in _ALL_EXTS:
        old = _avatar_path(user_id, old_ext)
        if os.path.exists(old):
            os.remove(old)
    with open(_avatar_path(user_id, ext), "wb") as f:
        f.write(content)


def read_avatar(user_id: int, ext: str) -> bytes:
    """Lädt das Profilbild von der Platte. Wirft ``FileNotFoundError`` falls fehlt."""
    path = _avatar_path(user_id, ext)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Avatar für Nutzer {user_id} nicht gefunden")
    with open(path, "rb") as f:
        return f.read()


def delete_avatar(user_id: int, ext: str | None) -> None:
    """Entfernt das Profilbild eines Nutzers (idempotent)."""
    exts = (ext,) if ext else _ALL_EXTS
    for e in exts:
        if not e:
            continue
        path = _avatar_path(user_id, e)
        if os.path.exists(path):
            os.remove(path)
