# TwoNote 📄

Eine persönliche Lern-Webapp zum Verwalten, Bearbeiten und Zusammenfassen von Dokumenten.

**Tech-Stack:**
- **Frontend:** Vue 3 + Vite + Pinia
- **Backend:** Python FastAPI
- **Speicher:** Google Drive (Service Account)
- **KI:** Google Gemini API (kostenlose Tier)

---

## Features

- 📁 Dokumente (PDF, Word) in Google Drive hochladen und verwalten
- ✏️ PDFs im Browser bearbeiten (Text schreiben, Markierungen, Checkboxen)
- 🤖 Dokumente mit Gemini AI zusammenfassen (auf Deutsch)
- 🔐 Mehrere Nutzer mit eigenem Login (JWT), gemeinsamer Drive-Ordner

---

## Voraussetzungen

1. **Docker + Docker Compose** installiert
2. **Google Cloud Projekt** mit aktivierter Google Drive API
3. **Service Account** mit JSON-Key (Drive-Ordner mit Service Account geteilt)
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
| `GOOGLE_SERVICE_ACCOUNT_CREDENTIALS` | JSON-Inhalt des Service Account Keys (eine Zeile) |
| `GOOGLE_DRIVE_FOLDER_ID` | ID des Drive-Ordners (aus der URL) |
| `GEMINI_API_KEY` | API Key von Google AI Studio |
| `JWT_SECRET_KEY` | Zufälliger Schlüssel (`openssl rand -hex 32`) |

### 2. Starten

```bash
docker-compose up --build
```

- Frontend: http://localhost:5173
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

## Google Drive einrichten

1. [Google Cloud Console](https://console.cloud.google.com) öffnen
2. Neues Projekt erstellen → **Google Drive API** aktivieren
3. **Service Account** erstellen → JSON-Key herunterladen
4. In Google Drive: Neuen Ordner erstellen → **mit der Service Account E-Mail teilen** (Editor-Rechte)
5. Folder ID aus der URL kopieren: `drive.google.com/drive/folders/`**`<FOLDER_ID>`**

---

## Projektstruktur

```
twonote/
├── docker-compose.yml
├── .env.example
├── frontend/          # Vue 3 App
└── backend/           # FastAPI App
```

---

## Entwicklung (ohne Docker)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```
