# Digicel Assessment — Django app

## Phase 2: Docker Compose (web + db)

From this directory (`DigicelAssessment/`):

1. Copy [.env.example](.env.example) to `.env` and set passwords.
2. Build and run:

   ```bash
   docker compose up --build
   ```

3. Open [http://localhost:8000](http://localhost:8000).

The `web` container runs `./entrypoint.sh`: waits for PostgreSQL, `migrate`, `seed_data --if-empty`, then `runserver`.

**Database host:** even if your `.env` sets `POSTGRES_HOST=localhost` for running Django on your PC, Compose overrides it to **`db`** for the `web` service so `entrypoint.sh` and Django reach Postgres correctly.

## Local development (venv + DB in Docker only)

```bash
cp .env.example .env
# Set POSTGRES_HOST=localhost when Django runs on the host.
docker compose up -d db
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data --if-empty
python manage.py runserver
```

## Seeded demo users

See repo root README or `core/management/commands/seed_data.py` for credential defaults (`admin`, `agent1`, `customer1`).

## Phase 3: Bootstrap UI (shared layout)

- Shared Bootstrap 5 base template (`templates/base.html`): role-aware nav, Django messages as dismissible alerts, POST logout in the navbar.
- Login (`/accounts/login/`) uses [`accounts/forms.py`](accounts/forms.py) `BootstrapAuthenticationForm` for Bootstrap field styling.
- Landing pages: `customer/`, `agent/`, `admin-portal/` (`templates/accounts/landing_*.html`).

**Quick verification:** sign in as `customer1`, `agent1`, and `admin` and confirm navbar items match each role (placeholders explain upcoming Complaints/Dashboard/Chatbot work). Visiting `/admin-portal/` while logged in as a customer must still return **403**.