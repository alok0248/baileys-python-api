Baileys WhatsApp + FastAPI Bridge
=================================

Overview
--------

This project is a small WhatsApp automation stack built from:

- **Baileys server (Node.js)** – connects to WhatsApp using the `@whiskeysockets/baileys` library, handles QR login, receives/sends messages and media, and forwards events to FastAPI via webhooks.
- **FastAPI server (Python)** – exposes a clean HTTP API, stores contacts/messages in SQLite/PostgreSQL, and serves as the main backend that your applications integrate with.

It supports:

- Login via QR code.
- Receiving text and media messages.
- Sending text and media messages.
- Storing messages and contacts in a database.
- Mapping WhatsApp LID JIDs to real phone numbers where possible, and returning **phone numbers** from the `/messages` API while still keeping the raw JID.


Architecture
------------

- `baileys-server/`
  - Express HTTP server.
  - Uses `@whiskeysockets/baileys@7.x` to connect to WhatsApp.
  - Pushes incoming events to FastAPI via HTTP (webhooks).
  - Exposes helper endpoints like `/qr`, `/messages`, `/receipts`, `/last-message/:user`, etc.

- `fastapi-server/`
  - FastAPI application that:
    - Receives webhooks from Baileys: `/webhook/message`, `/webhook/media`, `/webhook/receipt`, `/webhook/presence`.
    - Stores contacts and messages in SQLite or PostgreSQL.
    - Exposes a stable API for your apps (send message, list messages, etc.).
  - Uses `db_config.json` for storage configuration and supports overriding the Postgres DSN via `POSTGRES_DSN` env.

- `Dockerfile` + `run_all.py`
  - Container image runs both Baileys and FastAPI inside a single container.
  - `run_all.py` ensures Node and Python dependencies exist and then starts:
    - Baileys on `NODE_PORT` (default `3000`).
    - FastAPI on `FASTAPI_HOST:FASTAPI_PORT` (default `0.0.0.0:3002` in Docker).


Tech Stack
----------

- **Node.js 20+**
  - `@whiskeysockets/baileys`
  - `express`
  - `node-fetch`
  - `qrcode`

- **Python 3.10+**
  - `fastapi`
  - `uvicorn`
  - `requests`
  - `psycopg2-binary`
  - `python-dotenv`

- **Databases**
  - SQLite (always available, used as baseline).
  - PostgreSQL (recommended for production).


Repository Layout
-----------------

- `baileys-server/` – Node/TypeScript WhatsApp bridge.
- `fastapi-server/` – Python FastAPI bridge, DB, and HTTP API.
- `Dockerfile` – Docker image definition for combined deployment.
- `run_all.py` – Orchestration script used inside Docker and for local convenience.
- `fastapi-server/db_config.json` – DB and media configuration:
  - `engine` – `"sqlite"` (default).
  - `sqlite_path` – path to SQLite DB.
  - `base_path` – base directory for media storage.
  - `user` – user-specific subfolder for media.
  - `postgres_dsn` – default Postgres DSN for Docker.


How to Pull the Project
-----------------------

Create a new GitHub repo (for example: `https://github.com/alok0248/baileys-python-api`) and then:

```bash
git clone https://github.com/alok0248/baileys-python-api.git
cd baileys-python-api
```

If this code is currently only on your local machine:

```bash
cd /path/to/baileys-python-api
git init
git add .
git commit -m "Initial import of Baileys + FastAPI bridge"
git branch -M main
git remote add origin https://github.com/alok048/baileys-python-api.git
git push -u origin main
```


Local Development (without Docker)
----------------------------------

### 1. Prerequisites

- Node.js 20+ and npm.
- Python 3.10+.
- (Optional but recommended) Docker to run PostgreSQL locally.


### 2. Install dependencies

From the project root:

```bash
cd fastapi-server
pip install --upgrade pip
pip install -r requirements.txt

cd ../baileys-server
npm install
```


### 3. Configure the database

Open `fastapi-server/db_config.json`:

```json
{
  "engine": "sqlite",
  "sqlite_path": "data/appdb.db",
  "base_path": "B:/whatsapp_store",
  "user": "default",
  "postgres_dsn": "postgresql://appuser:apppassword@postgres:5432/appdb"
}
```

For local development:

- You can leave `engine` as `"sqlite"` and not use Postgres.
- Or you can run Postgres locally (for example on port 5433) and override the DSN via environment:

```bash
export POSTGRES_DSN="postgresql://appuser:apppassword@localhost:5433/appdb"
```

The code uses:

- `POSTGRES_DSN` env if set.
- Otherwise `postgres_dsn` from `db_config.json`.


### 4. Start Baileys server

In one terminal:

```bash
cd baileys-server
npm run start
```

This starts the WhatsApp bridge (default on port `3000`).


### 5. Start FastAPI server

In another terminal:

```bash
cd fastapi-server

# Optional: If you want to use local Postgres
export POSTGRES_DSN="postgresql://appuser:apppassword@localhost:5433/appdb"

python main.py
```

By default FastAPI serves on `http://0.0.0.0:3002`.


### 6. Verify

- FastAPI health:

  ```bash
  curl http://localhost:3002/health
  ```

- Baileys QR endpoint (through FastAPI helper):

  ```bash
  curl http://localhost:3002/qr
  ```

Or use your browser to open `http://localhost:3002/docs` for the interactive Swagger UI.


Docker Deployment
-----------------

### 1. Build image

From the project root:

```bash
docker build -t baileys-python-api .
```


### 2. Run PostgreSQL in Docker

Example:

```bash
docker run -d --name postgres \
  -e POSTGRES_DB=appdb \
  -e POSTGRES_USER=appuser \
  -e POSTGRES_PASSWORD=apppassword \
  -p 5432:5432 \
  postgres:15
```


### 3. Run the Baileys + FastAPI container

```bash
docker run -d --name baileys-python-api \
  --restart=always \
  -p 3000:3000 \
  -p 3002:3002 \
  --link postgres:postgres \
  -v /path/on/host/fastapi-server/db_config.json:/app/fastapi-server/db_config.json:ro \
  baileys-python-api
```

Notes:

- Inside the container, `fastapi-server/db.py` reads `db_config.json`, whose `postgres_dsn` should point to `postgres:5432` (as in the example).
- `--restart=always` ensures the container auto-starts in the background when Docker or the host reboots.


Configuration Details
---------------------

### `fastapi-server/db_config.json`

- `engine` – `"sqlite"` or `"postgres"`. SQLite is always initialized; Postgres is used when DSN is present.
- `sqlite_path` – path to SQLite DB file.
- `base_path` + `user` – base media directory; incoming and outgoing media are stored under:

  - `<base_path>/<user>/incoming`
  - `<base_path>/<user>/outgoing`

- `postgres_dsn` – default DSN used inside Docker (for example: `postgresql://appuser:apppassword@postgres:5432/appdb`).
- `POSTGRES_DSN` env – if set, overrides `postgres_dsn` at runtime.


Key Endpoints and Usage
-----------------------

All endpoints below are exposed by FastAPI on `http://<host>:3002`.

### Health

- `GET /health` – basic health check.


### WhatsApp Login

- `GET /qr` – fetches raw QR JSON from Baileys (`/qr`).
- `GET /whatsapp/qr` – unified QR status:
  - `{"status": "connected"}` if already logged in.
  - `{"status": "login_required"}` if no QR is available yet.
  - Or a payload containing a `qr` image data URL to be shown and scanned.

- `GET /whatsapp/me` – info about the currently logged-in WhatsApp user.


### Messaging

- `POST /send` – send a text message:

  Request body:

  ```json
  {
    "to": "91954xxxxxxx",
    "message": "Hello from FastAPI"
  }
  ```

  - `to` can be a phone number or a full JID; the Baileys server normalizes to `@s.whatsapp.net`.

- `GET /messages` – list recent incoming messages stored **in memory** on the Baileys side, returned via FastAPI.

  Each item looks like:

  ```json
  {
    "from": "919xxxxxxxx",
    "jid": "278868065796127@lid",
    "phone": "919xxxxxxxxx",
    "message": "Hello",
    "timestamp": 1768647418116
  }
  ```

  Notes:

  - Baileys receives some identifiers in `@lid` form.
  - The Node server uses Baileys v7 features (`remoteJidAlt` / `participantAlt`) to resolve phone numbers where possible.
  - FastAPI rewrites:
    - `from` → phone number (for easier use in clients).
    - Adds `jid` → original JID (LID or `@s.whatsapp.net`) when available.


### Media

- `POST /send/media` – send media file:

  ```json
  {
    "to": "9195xxxxxxxx",
    "filePath": "/absolute/path/to/file.jpg",
    "caption": "Check this out"
  }
  ```

  The FastAPI server normalizes the outgoing file path to the configured `OUTGOING_BASE_DIR` and stores the outgoing message in the DB.

- `GET /media/{filename}` – proxy to Baileys `/media/{filename}` for incoming media downloads.


### Receipts and Presence (internal)

- `POST /webhook/receipt` – used internally by Baileys to update message delivery/read status in the DB.
- `POST /webhook/message` – used internally by Baileys to store incoming text messages in the DB.
- `POST /webhook/media` – used internally for incoming media messages.
- `POST /webhook/presence` – used internally to update contact presence info.

Your applications typically do **not** call these webhooks directly; they are used between Baileys and FastAPI.


Database Behavior (Messages and Contacts)
----------------------------------------

- Every incoming or outgoing message is stored in `messages` with:
  - `message_id`
  - `contact_id`
  - `direction` (`in` / `out`)
  - `message_type` (`text` / `media`)
  - `content`, `media_path`, `timestamp`, `status`

- Every contact is stored in `contacts` with:
  - `jid` – raw JID (can be `@lid` or `@s.whatsapp.net`).
  - `phone` – resolved phone number when available.
  - `name`, `last_seen_at`, `is_online`, etc.

The contact upsert logic:

- Prefers a real phone number over a raw LID.
- If an existing contact has `phone` equal to the numeric part of a LID and later a real phone is resolved, the phone is updated.


How to Push to GitHub
---------------------

Once you are happy with the project locally:

```bash
cd /path/to/baileys-python-api

git add .
git commit -m "Baileys WhatsApp + FastAPI bridge initial version"
git push -u origin main
```

You can then link to this README on your GitHub repository so users can:

- Clone the project.
- Set up the environment.
- Run it locally or via Docker.
- Understand how to use the main endpoints.


Author
------

- Name: Your Name
- GitHub: https://github.com/alok0248
- Email: alokkumar2812@gmail.com

