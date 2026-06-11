# TwoNote 📄

Eine persönliche Lern-Webapp zum Verwalten, Bearbeiten und Zusammenfassen von Dokumenten.

**Tech-Stack:**
- **Frontend:** Vue 3 + Vite + Pinia (ausgeliefert über Nginx)
- **Backend:** Python FastAPI
- **Speicher:** Google Drive (OAuth2 / Refresh Token)
- **KI:** Google Gemini API (kostenlose Tier)

---

## Features

- 📁 Dokumente (PDF, Word) in Google Drive hochladen und verwalten
- ✏️ PDFs im Browser bearbeiten (Text schreiben, Markierungen, Checkboxen)
- 🤖 Dokumente mit Gemini AI zusammenfassen (auf Deutsch)
- 🔐 Mehrere Nutzer mit eigenem Login (JWT), gemeinsamer Drive-Ordner

---

## Architektur

```
Browser ──> Nginx (Frontend, :8080) ──> FastAPI (Backend, :8000)
                                           ├── SQLite      (User-Accounts, JWT)
                                           ├── Google Drive (Dateispeicher, OAuth2)
                                           └── Gemini API   (Zusammenfassungen)
```

- Die **Vue-SPA** wird von **Nginx** ausgeliefert; Nginx leitet alle `/api/*`-Anfragen an das Backend weiter (Upload-Limit 100 MB).
- Das **FastAPI-Backend** hat drei Bereiche: `auth` (Login/Registrierung), `files` (Datei-CRUD gegen Drive) und `ai` (Gemini-Zusammenfassung).
- **Nutzer-Accounts** liegen in einer **SQLite**-Datenbank (Passwörter via bcrypt). Die Authentifizierung läuft über **JWT** (HS256), das im Browser im `localStorage` gehalten und per Axios-Interceptor an jede Anfrage gehängt wird.
- **Dokumente** liegen ausschließlich in **Google Drive** und werden von allen Nutzern geteilt.

---

## Voraussetzungen

1. **Docker + Docker Compose** installiert
2. **Google Cloud Projekt** mit aktivierter Google Drive API
3. **OAuth 2.0 Client-ID** (Typ *Desktop-App*) + **Refresh Token** (via `get_refresh_token.py`)
4. **Gemini API Key** von [aistudio.google.com](https://aistudio.google.com/apikey)

---

## Setup

### 1. Umgebungsvariablen konfigurieren

```bash
cp .env.example .env
# .env mit deinen Credentials befüllen
```

**Benötigte Werte in `.env`:**

| Variable | Beschreibung |
|---|---|
| `GOOGLE_CLIENT_ID` | OAuth 2.0 Client-ID (`...apps.googleusercontent.com`) |
| `GOOGLE_CLIENT_SECRET` | OAuth 2.0 Client Secret |
| `GOOGLE_REFRESH_TOKEN` | Refresh Token (Ausgabe von `get_refresh_token.py`) |
| `GOOGLE_DRIVE_FOLDER_ID` | ID des Drive-Ordners (aus der URL) |
| `GEMINI_API_KEY` | API Key von Google AI Studio |
| `JWT_SECRET_KEY` | Zufälliger Schlüssel (`openssl rand -hex 32`) |
| `JWT_EXPIRE_MINUTES` | Gültigkeit des JWT in Minuten (Standard: `1440`) |
| `CORS_ORIGINS` | Erlaubte Frontend-Origins, kommagetrennt (z.B. `http://localhost:8080`) |

### 2. Starten

```bash
docker-compose up --build
```

- Frontend: http://localhost:8080
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 3. Ersten Nutzer anlegen

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "dein_passwort"}'
```

> **Hinweis:** Solange keine Nutzer existieren, ist Register offen. Danach nur noch für eingeloggte Nutzer.

---

## Google Drive einrichten (OAuth2)

1. [Google Cloud Console](https://console.cloud.google.com) öffnen
2. Neues Projekt erstellen → **Google Drive API** aktivieren
3. Unter **APIs & Dienste → Anmeldedaten**: **OAuth 2.0 Client-ID** erstellen → Anwendungstyp **Desktop-App**
4. Token beschaffen – im Projektverzeichnis ausführen:
   ```bash
   python3 get_refresh_token.py
   ```
   Das Skript öffnet den Google-Login und gibt anschließend `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` und `GOOGLE_REFRESH_TOKEN` aus → in `.env` eintragen.
5. In Google Drive: Neuen Ordner anlegen und die Folder-ID aus der URL kopieren:
   `drive.google.com/drive/folders/`**`<FOLDER_ID>`** → als `GOOGLE_DRIVE_FOLDER_ID` eintragen.

---

## API-Endpunkte

Vollständige interaktive Doku unter http://localhost:8000/docs (Swagger UI).

| Methode | Pfad | Beschreibung |
|---|---|---|
| `POST` | `/api/auth/register` | Nutzer registrieren (erster Nutzer offen, danach nur eingeloggt) |
| `POST` | `/api/auth/register-auth` | Nutzer registrieren (nur eingeloggt) |
| `POST` | `/api/auth/login` | Login → JWT Token |
| `GET` | `/api/auth/me` | Aktuellen Nutzer abfragen |
| `GET` | `/api/files` | Dateien/Ordner auflisten (optional `?folder_id=`) |
| `POST` | `/api/files/folder` | Ordner anlegen |
| `POST` | `/api/files/upload` | Datei (PDF/Word) hochladen |
| `GET` | `/api/files/{id}/download` | Datei herunterladen |
| `PUT` | `/api/files/{id}` | Datei-Inhalt überschreiben (z.B. bearbeitetes PDF) |
| `DELETE` | `/api/files/{id}` | Datei löschen |
| `POST` | `/api/files/{id}/summarize` | Dokument mit Gemini zusammenfassen |

---

## Projektstruktur

```
twonote/
├── docker-compose.yml
├── .env.example
├── get_refresh_token.py    # OAuth2 Refresh Token beschaffen
├── frontend/               # Vue 3 + Vite App (über Nginx ausgeliefert)
│   └── src/                # views, components, stores (Pinia), api, router
└── backend/                # FastAPI App
    └── app/
        ├── config.py       # Einstellungen aus .env
        ├── database.py     # SQLite / SQLModel
        ├── models/         # User-Modell & Schemas
        ├── routes/         # auth, files, ai
        └── services/       # auth (JWT), drive (Google Drive), gemini (KI)
```

---

## Entwicklung (ohne Docker)

**Backend** (läuft auf http://localhost:8000):
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend** (Vite-Dev-Server auf http://localhost:5173):
```bash
cd frontend
npm install
npm run dev
```

> **Hinweis:** Im Dev-Modus muss `CORS_ORIGINS` in der `.env` den Vite-Dev-Server enthalten, z.B. `http://localhost:5173`.
