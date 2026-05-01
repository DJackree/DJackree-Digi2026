# DigicelAssessment

Digicel Software Development & Design Engineer Interview — Assessment

## Phase 1 (foundation) — status

Implements **database foundation**: Django project, PostgreSQL settings, `accounts.UserProfile`, customer plan/account/usage/payment models, admin registration, Docker Compose `db` service, `.env.example`, and `seed_data --if-empty`.

Auth views, Bootstrap UI, complaints, dashboard, and chatbot are planned for later phases.

### Prerequisites

- Python 3.12+ (recommended)
- Docker (optional, for PostgreSQL only via Compose)

### Quick start — local Postgres

The Django project lives in [`DigicelAssessment/`](DigicelAssessment/). Run Docker Compose from the **repository root** so it picks up `DigicelAssessment/.env`.

1. Copy environment template and set a database password:

   ```bash
   cp DigicelAssessment/.env.example DigicelAssessment/.env
   ```

2. Start PostgreSQL:

   ```bash
   docker compose up -d db
   ```

3. Create virtualenv and install dependencies (inside the app directory):

   ```bash
   cd DigicelAssessment
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. Run migrations:

   ```bash
   python manage.py migrate
   ```

5. Seed foundation data (runs once unless DB is wiped):

   ```bash
   python manage.py seed_data --if-empty
   ```

6. Seed creates admin user — visit Django admin:

   ```bash
   python manage.py runserver
   ```

   Then open `/admin/` and log in as `admin`.

### Seeded demo credentials

| Role     | Username    | Password            |
|---------|-------------|---------------------|
| Admin   | `admin`     | `AdminPass123!`     |
| Agent   | `agent1`    | `AgentPass123!`     |
| Customer| `customer1` | `CustomerPass123!` |

Agents: `agent1` … `agent3`. Customers: `customer1` … `customer5`.

### Verify idempotent seed

From `DigicelAssessment/` (with venv active):

```bash
python manage.py seed_data --if-empty
python manage.py seed_data --if-empty
```

The second run should print **Skipping seed_data: database not empty.**
