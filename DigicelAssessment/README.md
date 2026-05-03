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

On a **fresh** database (`seed_data` without `--if-empty`), the seed also creates **15 demo complaints** (all categories/statuses, SLA breach examples, status history, internal notes on assigned tickets), plus **2 network outages** (including an active outage in **Kingston**, matching `customer1`). If users already exist, `seed_data --if-empty` skips everything—including complaints—by design.

## Complaints module (Phase 2 backend)

Routes (role-protected):

- Customer: `/complaints/`, `/complaints/new/`, `/complaints/<reference>/`
- Agent: `/agent/complaints/` (optional `?status=&category=` filters), `/agent/complaints/<reference>/` (+ POST endpoints for status, notes, escalation)
- Admin: `/admin-portal/dashboard/`, `/admin-portal/complaints/` (optional `?status=&category=&agent=&sla_breach=1`), `/admin-portal/complaints/<reference>/` (+ POST assign/status)

Phase 3 templates add Bootstrap polish (badges, clearer SLA indicators), customer-safe timelines (no internal-note leakage), admin/agent filters, and landing-page shortcuts.

Workflow rules live in [`complaints/services.py`](complaints/services.py). Automated tests: `python manage.py test complaints dashboard` (requires a reachable Postgres DB matching `.env`).

## Phase 3: Bootstrap UI (shared layout)

- Shared Bootstrap 5 base template (`templates/base.html`): role-aware nav, Django messages as dismissible alerts, POST logout in the navbar.
- Login (`/accounts/login/`) uses [`accounts/forms.py`](accounts/forms.py) `BootstrapAuthenticationForm` for Bootstrap field styling.
- Landing pages: `customer/`, `agent/`, `admin-portal/` (`templates/accounts/landing_*.html`).

**Quick verification:** sign in as `customer1`, `agent1`, and `admin` and exercise the Complaints/Dashboard links in the navbar (`/complaints/`, `/agent/complaints/`, `/admin-portal/dashboard/`). Visiting `/admin-portal/` while logged in as a customer must still return **403**.

## AI chatbot — Phase 1 (database persistence)

Phase 1 adds the `chatbot` app with **`ChatSession`** and **`ChatMessage`** models plus admin registration. Applying migrations creates the transcript tables; **no scripted chat transcripts** are seeded (history is meant to accumulate via the UI once Phase 2/3 ship).

After `python manage.py migrate`, you can inspect `ChatSession` / `ChatMessage` in Django admin (`/admin/`).

Phase 2+ will route customers through Groq using `GROQ_API_KEY` (see [.env.example](.env.example)); **secrets are never stored in chat tables**.

### Seed coverage for upcoming chat intents (fresh DB only)

After a **full** `seed_data` run on an empty DB, each seeded customer (`customer1` … `customer5`) has:

- A **service plan** and **customer account** (plan / balance intents)
- **`AccountUsage`** for the **current billing month** (data usage intent)
- At least one **`Payment`** (last payment intent)
- Several customers—including **`customer1`**—have complaints in **non-terminal** statuses (Open, In Progress, Escalated) for the “open complaints” flow
- An active **`NetworkOutage` in Kingston** aligns with **`customer1`**’s account region (**active outages / faults** intent)

If your database already has users, `seed_data --if-empty` **skips** those records; reset the DB if you need the demo rows for intent testing.

**Tests:** `python manage.py test chatbot` (requires Postgres reachable using your `.env`, same as the complaints/dashboard suite).