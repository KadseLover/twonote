# TwoNote 📄

Eine persönliche Lern-Webapp zum Verwalten, Bearbeiten und Zusammenfassen von Dokumenten.

**Tech-Stack:**
- **Frontend:** Vue 3 + Vite + Pinia (ausgeliefert über Nginx)
- **Backend:** Python FastAPI
- **Bearbeitung:** OnlyOffice Document Server (Echtzeit-Co-Editing)
- **Speicher:** Lokales Dateisystem auf dem Server (Docker-Volume)
- **KI:** Google Gemini API (kostenlose Tier)

---

## Features

- 📁 Dokumente (PDF, Word, Excel, PowerPoint) hochladen und lokal auf dem Server verwalten
- ✏️ Dateien direkt im Browser mit **OnlyOffice** bearbeiten – inkl. **Echtzeit-Co-Editing** (mehrere Nutzer gleichzeitig); gespeichert wird automatisch zurück in dieselbe Datei
- 🤖 Dokumente mit Gemini AI zusammenfassen (auf Deutsch)
- 🔐 Mehrere Nutzer mit eigenem Login (JWT), gemeinsamer Dateibestand

---

## Architektur

```
Browser ──> Nginx (Frontend, :8080) ──> FastAPI (Backend, :8000)
   │                                       ├── SQLite           (User-Accounts, JWT, Datei-Metadaten)
   │                                       ├── data/files/      (lokaler Dateispeicher)
   │                                       └── Gemini API        (Zusammenfassungen)
   │                                              ▲
   └──> OnlyOffice Document Server (:8082) ───────┘  (server-zu-server: Datei laden + speichern)
```

- Die **Vue-SPA** wird von **Nginx** ausgeliefert; Nginx leitet alle `/api/*`-Anfragen an das Backend weiter (Upload-Limit 100 MB).
- Das **FastAPI-Backend** hat vier Bereiche: `auth` (Login/Registrierung), `files` (Datei-CRUD lokal), `ai` (Gemini-Zusammenfassung) und `onlyoffice` (Editor-Config, Download & Speicher-Callback).
- **Nutzer-Accounts** und **Datei-Metadaten** (Ordnerstruktur, Namen, Größen) liegen in einer **SQLite**-Datenbank (Passwörter via bcrypt). Die Authentifizierung läuft über **JWT** (HS256), das im Browser im `localStorage` gehalten und per Axios-Interceptor an jede Anfrage gehängt wird.
- **Dokumente** liegen als Dateien unter `data/files/` auf dem Server (Docker-Volume `backend_data:/app/data`) und werden von allen Nutzern geteilt.
- **Bearbeiten:** Der Browser lädt den OnlyOffice-Editor vom **Document Server** und öffnet darin die Datei. Der Document Server holt die Originaldatei server-zu-server vom Backend (`document.url`) und meldet Speicherstände an den Backend-`callbackUrl` zurück – beide URLs sind per JWT signiert (`ONLYOFFICE_JWT_SECRET`). Mehrere Nutzer am selben Dokument editieren dank gemeinsamem `document.key` in Echtzeit gemeinsam.

---

## Voraussetzungen

1. **Docker + Docker Compose** installiert
2. **Gemini API Key** von [aistudio.google.com](https://aistudio.google.com/apikey)
3. **Genügend RAM** für den OnlyOffice Document Server (Richtwert ≥ 2 GB zusätzlich; er bündelt PostgreSQL/RabbitMQ/Redis)

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
| `ONLYOFFICE_JWT_SECRET` | Geteiltes Geheimnis Backend ↔ Document Server (`openssl rand -hex 32`) |
| `ONLYOFFICE_PUBLIC_URL` | Vom Browser erreichbare URL des Document Servers (lokal `http://localhost:8082`, prod z.B. `https://docs.deine-domain.de`) |
| `BACKEND_INTERNAL_URL` | Backend-URL aus Sicht des Document Servers (Docker-intern, Standard `http://backend:8000`) |

> **Hinweis:** `ONLYOFFICE_JWT_SECRET` muss exakt mit dem `JWT_SECRET` des `documentserver`-Containers übereinstimmen (in `docker-compose.yml` bereits aus derselben Variable gespeist). Hinter einem Tunnel/HTTPS muss `ONLYOFFICE_PUBLIC_URL` ebenfalls per HTTPS erreichbar sein (eigene Subdomain), sonst blockiert der Browser den Editor (Mixed Content).

### 1b. Reverse Proxy (Produktion mit eigener Domain)

`docker-compose.yml` enthält einen **Caddy**-Service, der TLS terminiert und nach Hostname
routet (Frontend bzw. Document Server). Die echte `Caddyfile` ist **server-lokal**
(in `.gitignore`, wird nie überschrieben) – Vorlage kopieren und Domains anpassen:

```bash
cp Caddyfile.example Caddyfile
# twonote.example.com / office.example.com durch deine (Sub-)Domains ersetzen
```

- Beide (Sub-)Domains müssen per DNS auf den Server zeigen (z.B. CNAME der Office-Subdomain
  auf den Haupt-Hostnamen, falls Dynamic DNS).
- `office.<domain>` muss derselbe Wert wie `ONLYOFFICE_PUBLIC_URL` sein.
- Caddy holt Let's-Encrypt-Zertifikate automatisch und unterstützt die WebSockets fürs Co-Editing.

### 2. Starten

```bash
docker-compose up --build
```

- Frontend: http://localhost:8080
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- OnlyOffice Document Server: http://localhost:8082 (Healthcheck: `http://localhost:8082/healthcheck` → `true`)

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
bestehende Zusammenfassungen erhalten bleiben. Danach können die
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
| `POST` | `/api/files/upload` | Datei (PDF/Word/Excel/PowerPoint) hochladen |
| `GET` | `/api/files/{id}/download` | Datei herunterladen |
| `DELETE` | `/api/files/{id}` | Datei löschen |
| `GET` | `/api/files/{id}/onlyoffice/config` | Signierte OnlyOffice-Editor-Config (App-Auth) |
| `GET` | `/api/files/{id}/onlyoffice/download` | Datei für den Document Server (signierter Token) |
| `POST` | `/api/files/{id}/onlyoffice/callback` | Speicher-Callback des Document Servers |
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
        ├── models/         # User, FileRecord, Summary, AiUsage …
        ├── routes/         # auth, files, ai, onlyoffice
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
>
> Zum Bearbeiten wird zusätzlich der Document Server benötigt – einzeln startbar mit `docker compose up documentserver`. Da der Container die Dateien server-zu-server unter `BACKEND_INTERNAL_URL` abholt, muss diese URL für ihn erreichbar sein (im reinen Host-Dev-Betrieb z.B. `http://host.docker.internal:8000`).
