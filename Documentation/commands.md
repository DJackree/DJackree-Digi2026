# Commands Reference

Commands for the Telecom Customer Portal assessment repo. The Django app lives in [`DigicelAssessment/`](../DigicelAssessment/); Docker Compose is run from the **repository root**.

## Prerequisites

- Python 3.12+ (recommended)
- Docker / Docker Compose (for PostgreSQL in a container)

## One-time environment file

From the **repository root**:

```bash
cp DigicelAssessment/.env.example DigicelAssessment/.env
```

Edit `DigicelAssessment/.env` and set `POSTGRES_PASSWORD` (and any other values) for local development. Do not commit `.env`.

## Database (PostgreSQL via Docker)

Start the database in the background:

```bash
docker compose up -d db
```

Stop containers (from repo root):

```bash
docker compose down
```

To reset the database data volume (destructive; use when you need a clean Postgres):

```bash
docker compose down -v
```

Then start `db` again and re-run migrations and seed.

## Python virtual environment and dependencies

From **`DigicelAssessment/`** (where `manage.py` and `requirements.txt` are):

**Windows (PowerShell or cmd):**

```bat
cd DigicelAssessment
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**Git Bash on Windows (recommended sequence):**

Run each line after the previous one succeeds:

```bash
cd DigicelAssessment
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**How to tell it worked:** After `source .venv/Scripts/activate`, `pip` should install into the venv, not your user profile. You should see paths containing `.venv\lib\site-packages` (or `.venv/lib/...`) and **no** line like `Defaulting to user installation because normal site-packages is not writeable`.

Optional check (Git Bash):

```bash
which python
which pip
```

Paths should point under `.venv/Scripts/` or `.venv\Scripts\`.

## Django: apply migrations

With the venv activated and Postgres running (`POSTGRES_HOST=localhost` in `.env` when Django runs on the host):

```bash
python manage.py migrate
```

## Django: seed foundation data

Idempotent: skips if users already exist when `--if-empty` is passed:

```bash
python manage.py seed_data --if-empty
```

Run twice to confirm the second run skips:

```bash
python manage.py seed_data --if-empty
python manage.py seed_data --if-empty
```

## Django: development server

```bash
python manage.py runserver
```

Default URL: `http://127.0.0.1:8000/` — admin at `/admin/` (after seeding, log in with the seeded admin user from the project README).

## Django: automated tests (`chatbot` app)

Runs the **PostgreSQL-backed** Django test suite for the **chatbot** app (session/message persistence, intent detection, customer-only API handling, mocked Groq paths, and related regression checks).

### What happens when you run this

1. Django connects to Postgres using **`DigicelAssessment/.env`** (same connection settings as `migrate`).
2. It creates an **empty, disposable database** whose name is your configured `POSTGRES_DB` with a **`test_` prefix** (for example **`test_telecom_portal`** when `POSTGRES_DB=telecom_portal`).
3. It applies **all migrations** to that test database.
4. It runs the tests defined under **`DigicelAssessment/chatbot/tests.py`** and prints pass/fail output.

Groq credentials are **not required** for the included tests—the suite **patches** `ask_groq` where it needs deterministic behavior. Postgres **must** be running and reachable (`connection timeout` / `OperationalError` during “Creating test database…” means Postgres is stopped or **`POSTGRES_HOST` / credentials / port** do not match your setup).

### When to run it

Before or while changing **`chatbot/`** routes, intents, contexts, prompts, Groq integration, or customer permissions.

### Command

From **`DigicelAssessment/`** with the virtual environment activated and Postgres running (from repo root: `docker compose up -d db`). When Django runs **on your machine** outside the Compose **`web`** service, **`POSTGRES_HOST=localhost`** should be set in `.env`:

```bash
python manage.py test chatbot -v 2
```

Optional: reuse an existing local test DB for faster repeats (drops less work between runs):

```bash
python manage.py test chatbot -v 2 --keepdb
```

Run chatbot tests together with other modules’ suites:

```bash
python manage.py test complaints dashboard chatbot -v 2
```

## Django: checks (optional)

```bash
python manage.py check
```

## Typical full flow (fresh clone)

1. `cp DigicelAssessment/.env.example DigicelAssessment/.env` — set password and variables.
2. `docker compose up -d db` — from repo root.
3. `cd DigicelAssessment` — `python -m venv .venv`, activate (`source .venv/Scripts/activate` in Git Bash), `python -m pip install --upgrade pip`, `pip install -r requirements.txt`.
4. `python manage.py migrate`
5. `python manage.py seed_data --if-empty`
6. `python manage.py runserver`

## Troubleshooting

### Git Bash: `bash: .venvScriptsactivate: command not found`

Do **not** chain activation with Windows cmd syntax on Git Bash:

```bash
# Wrong in Git Bash — backslashes are not a path separator here
.venv\Scripts\activate
```

Use **`source`** and **forward slashes** (run each step separately, or use `source` in the chain):

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Or one line:

```bash
python -m venv .venv && source .venv/Scripts/activate && python -m pip install --upgrade pip && pip install -r requirements.txt
```

### `docker compose` must be run from repo root

If you are inside `DigicelAssessment/DigicelAssessment/`, `cd` up two levels (or open a shell at the repo root) so Compose finds `docker-compose.yml`.

## Notes

- `docker compose` reads Postgres settings from `DigicelAssessment/.env` via the `db` service `env_file` in the root [`docker-compose.yml`](../docker-compose.yml).
- Django loads the same `DigicelAssessment/.env` via `python-dotenv` in settings when you run commands from the app directory.
