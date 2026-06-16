# TwoNote 📄

Eine persönliche Lern-Webapp zum Verwalten, Bearbeiten und Zusammenfassen von Dokumenten.

**Tech-Stack:**
- **Frontend:** Vue 3 + Vite + Pinia (ausgeliefert über Nginx)
- **Backend:** Python FastAPI
- **Speicher:** Lokales Dateisystem auf dem Server (Docker-Volume)
- **KI:** Google Gemini API (kostenlose Tier)

---

## Features

- 📁 Dokumente (PDF, Word) hochladen und lokal auf dem Server verwalten
- ✏️ PDFs im Browser bearbeiten (Text schreiben, Markierungen, Checkboxen)
- 🤖 Dokumente mit Gemini AI zusammenfassen (auf Deutsch)
- 🔐 Mehrere Nutzer mit eigenem Login (JWT), gemeinsamer Dateibestand

---

## Architektur

```
Browser ──> Nginx (Frontend, :8080) ──> FastAPI (Backend, :8000)
                                           ├── SQLite           (User-Accounts, JWT, Datei-Metadaten)
                                           ├── data/files/      (lokaler Dateispeicher)
                                           └── Gemini API        (Zusammenfassungen)
```

- Die **Vue-SPA** wird von **Nginx** ausgeliefert; Nginx leitet alle `/api/*`-Anfragen an das Backend weiter (Upload-Limit 100 MB).
- Das **FastAPI-Backend** hat drei Bereiche: `auth` (Login/Registrierung), `files` (Datei-CRUD lokal) und `ai` (Gemini-Zusammenfassung).
- **Nutzer-Accounts** und **Datei-Metadaten** (Ordnerstruktur, Namen, Größen) liegen in einer **SQLite**-Datenbank (Passwörter via bcrypt). Die Authentifizierung läuft über **JWT** (HS256), das im Browser im `localStorage` gehalten und per Axios-Interceptor an jede Anfrage gehängt wird.
- **Dokumente** liegen als Dateien unter `data/files/` auf dem Server (Docker-Volume `backend_data:/app/data`) und werden von allen Nutzern geteilt.

---

## Voraussetzungen

1. **Docker + Docker Compose** installiert
2. **Gemini API Key** von [aistudio.google.com](https://aistudio.google.com/apikey)

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

## Dateispeicher

Dokumente werden lokal unter `data/files/` im Backend gespeichert (Docker-Volume
`backend_data:/app/data`, gemeinsam mit der SQLite-DB). Es ist keine Cloud-Konfiguration nötig.

### Migration von einer früheren Google-Drive-Installation (einmalig)

Wer von einer älteren, Drive-basierten Version kommt, übernimmt die vorhandenen Drive-Daten
mit dem einmaligen Skript `backend/migrate_drive_to_local.py`. Dazu müssen die alten
Google-Credentials (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`,
`GOOGLE_DRIVE_FOLDER_ID`) noch in `.env` stehen und die `google-*`-Pakete installiert sein:

```bash
cd backend
pip install google-api-python-client google-auth google-auth-httplib2
python migrate_drive_to_local.py
```

Das Skript lädt den kompletten Drive-Ordnerbaum nach `data/files/` und legt die Metadaten in
der DB an. Die ursprünglichen Drive-IDs werden als lokale Datei-IDs übernommen, sodass
bestehende Notizen/Annotationen und Zusammenfassungen erhalten bleiben. Danach können die
`GOOGLE_*`-Variablen aus `.env` entfernt werden.

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
| `DELETE` | `/api/files/{id}` | Datei löschen |
| `POST` | `/api/files/{id}/summarize` | Dokument mit Gemini zusammenfassen |

---

## Projektstruktur

```
twonote/
├── docker-compose.yml
├── .env.example
├── frontend/               # Vue 3 + Vite App (über Nginx ausgeliefert)
│   └── src/                # views, components, stores (Pinia), api, router
└── backend/                # FastAPI App
    ├── migrate_drive_to_local.py  # einmalige Drive→lokal Migration (optional)
    └── app/
        ├── config.py       # Einstellungen aus .env
        ├── database.py     # SQLite / SQLModel
        ├── models/         # User, FileRecord, Annotation, Summary …
        ├── routes/         # auth, files, ai
        └── services/       # auth (JWT), storage (lokale Dateien), gemini (KI)
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
