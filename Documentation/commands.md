# Commands reference

Commands for the Telecom Customer Portal. The Django project and **Docker Compose file** live in [`DigicelAssessment/`](../DigicelAssessment/) (same directory as `manage.py`).

Quick start: root [`README.md`](../README.md) (`.env`, `docker compose up`).

## Prerequisites

- **Docker** and **Docker Compose** (recommended way to run the full stack)
- **Python 3.12+** (optional, for running Django on the host against Compose Postgres)
- **PostgreSQL** available (via Docker as below)

## One-time environment file

From the **repository root**:

```bash
cp DigicelAssessment/.env.example DigicelAssessment/.env
```

Edit `DigicelAssessment/.env`. Set `POSTGRES_*`, `DJANGO_SECRET_KEY`, and `GROQ_API_KEY` for chatbot testing. **Do not commit** `.env`.

---

## Full stack with Docker (primary)

All `docker compose` commands are run from **`DigicelAssessment/`** (where `docker-compose.yml` is).

**First run** (build images, migrate, seed if empty, start server):

```bash
cd DigicelAssessment
docker compose up --build
```

**Later runs:**

```bash
cd DigicelAssessment
docker compose up
```

- App URL: **http://localhost:8000**
- The `web` service sets `POSTGRES_HOST=db` automatically; keep `POSTGRES_HOST=db` in `.env` for consistency, or rely on Compose overrides when using `web`.

**Stop:**

```bash
cd DigicelAssessment
docker compose down
```

**Reset database volume** (destructive — removes Postgres data; next `up` re-migrates and re-seeds if empty):

```bash
cd DigicelAssessment
docker compose down -v
```

**Database only** (run Django on your machine; use `POSTGRES_HOST=localhost` in `.env`):

```bash
cd DigicelAssessment
docker compose up -d db
```

---

## Python virtual environment (host Django)

From **`DigicelAssessment/`** (where `manage.py` and `requirements.txt` are).

**Windows (PowerShell or cmd):**

```bat
cd DigicelAssessment
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Git Bash on Windows:**

```bash
cd DigicelAssessment
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Use `POSTGRES_HOST=localhost` in `.env` when Postgres is exposed from Docker on port 5432.

## Django: apply migrations

With venv activated and Postgres reachable:

```bash
cd DigicelAssessment
python manage.py migrate
```

## Django: seed data

Idempotent when using `--if-empty` (skips if any user exists):

```bash
cd DigicelAssessment
python manage.py seed_data --if-empty
```

## Django: development server (host)

```bash
cd DigicelAssessment
python manage.py runserver
```

- App: **http://127.0.0.1:8000/**
- Admin: **http://127.0.0.1:8000/admin/**

Seeded users: root [`README.md`](../README.md).

## Django: automated tests

The suite uses **PostgreSQL** (same family as production). With **`db`** running and **`POSTGRES_HOST=localhost`** in `.env` when tests run on the host:

```bash
cd DigicelAssessment
python manage.py test -v 2
```

Focused runs (apps that currently ship tests):

```bash
python manage.py test accounts customers complaints dashboard chatbot -v 2
```

Chatbot-only (Groq is **mocked** where needed; no API key required for tests):

```bash
python manage.py test chatbot -v 2
```

Optional faster repeat (reuses test DB):

```bash
python manage.py test -v 2 --keepdb
```

If you see **connection timeout / OperationalError** while creating the test database, ensure Postgres is up and `POSTGRES_HOST`, port, and credentials match (`db` vs `localhost`).

## Django: system check (optional)

```bash
cd DigicelAssessment
python manage.py check
```

---

## Typical flows

### Fresh clone, Docker only

1. `cp DigicelAssessment/.env.example DigicelAssessment/.env` and edit values (include `GROQ_API_KEY` to exercise the chatbot).
2. `cd DigicelAssessment && docker compose up --build`
3. Open http://localhost:8000 and sign in with seeded accounts (see root README).

### Fresh clone, Django on host + Compose DB

1. Copy and edit `.env`; set **`POSTGRES_HOST=localhost`**.
2. `cd DigicelAssessment && docker compose up -d db`
3. Create venv, `pip install -r requirements.txt`
4. `python manage.py migrate`
5. `python manage.py seed_data --if-empty`
6. `python manage.py runserver`

---

## Troubleshooting

### `docker compose` cannot find compose file

Run Compose from **`DigicelAssessment/`**, not the repository root (unless you add a wrapper compose file at root).

### Git Bash: `.venvScriptsactivate: command not found`

Use:

```bash
source .venv/Scripts/activate
```

not `\.venv\Scripts\activate`.

### Postgres password / host mismatch

- **Inside `web` container**: host must be **`db`** (Compose service name); the compose file overrides `POSTGRES_HOST` for `web`.
- **Django on host**: use **`localhost`** and exposed port `5432`.

### Seed did not create complaints

`seed_data --if-empty` skips if **any** user exists. Use a fresh DB (`docker compose down -v`) or a new database before re-seeding.

## Notes

- Compose reads **`DigicelAssessment/.env`** for the `web` service `env_file`.
- Django loads the same file via `python-dotenv` in `config/settings.py` when you run `manage.py` from `DigicelAssessment/`.
