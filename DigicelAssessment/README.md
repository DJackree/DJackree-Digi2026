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

## AI chatbot

### Phase 1 — persistence

Adds **`ChatSession`** and **`ChatMessage`** models plus admin visibility. Applying migrations creates the transcript tables.

### Phase 2 — backend (Groq-backed, customer scoped)

Customers only — agents/admins receive **403** (`GET /chatbot/`).

Routes:

- `GET /chatbot/` — minimal transcript page [`templates/chatbot/chat.html`](templates/chatbot/chat.html) (loads latest session or creates one)
- `POST /chatbot/messages/` — JSON `{ "session_id": <int>, "message": "<text>" }` returns `{ ok, intent, message, session_id }` plus persisted rows
- `POST /chatbot/sessions/new/` — JSON `{}` creates a fresh session `{ ok, session_id }`

Requirements:

1. **`GROQ_API_KEY`** in `.env` (see [.env.example](.env.example)). If missing, supported intents persist a polite **setup** reply (no hallucinated balances).
2. JSON POST endpoints require the normal Django **CSRF** cookie/header (the template’s `fetch` sends `X-CSRFToken`).

Optional Django settings/env overrides (`config/settings.py` reads env unless noted):

- `GROQ_MODEL` — defaults to **`llama-3.1-8b-instant`**
- `GROQ_TIMEOUT_SECONDS` — HTTP timeout for Groq SDK (default **30**)
- `GROQ_MAX_COMPLETION_TOKENS` — cap completion tokens (default **512**)
- `CHATBOT_MESSAGE_MAX_LENGTH` — incoming message ceiling (default **1000**, matches prior plan)
- `CHATBOT_DEFAULT_CURRENCY` — shown in ACCOUNT_CONTEXT payloads (default **JMD**)

**Secrets are never persisted** inside chat tables beyond the grounded assistant reply itself.

Automated regression tests: `python manage.py test chatbot` (Postgres required like other suites).

### Seed coverage for chat intents (fresh DB only)

After a **full** `seed_data` run on an empty DB, each seeded customer (`customer1` … `customer5`) has:

- A **service plan** and **customer account** (plan / balance intents)
- **`AccountUsage`** for the **current billing month** (data usage intent)
- At least one **`Payment`** (last payment intent)
- Several customers—including **`customer1`**—have complaints in **non-terminal** statuses (Open, In Progress, Escalated) for the “open complaints” flow
- An active **`NetworkOutage` in Kingston** aligns with **`customer1`**’s account region (**active outages / faults** intent)

If your database already has users, `seed_data --if-empty` **skips** those records; reset the DB if you need the demo rows for intent testing.