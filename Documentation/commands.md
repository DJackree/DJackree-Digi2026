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
