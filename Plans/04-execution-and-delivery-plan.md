# Execution And Delivery Plan

## Purpose

This plan turns the architecture and module designs into an ordered 3-4 day build strategy. It prioritizes a working end-to-end assessment submission over optional polish.

## Delivery Principles

- Build the vertical path early: Docker, login, one role page, database, and a simple template.
- Keep the stack Django-native.
- Put business rules in services or forms, not only templates.
- Seed realistic data early so the UI and chatbot can be tested continuously.
- Prefer clear README instructions and predictable reviewer experience over advanced features.

## Day 0 Or Start Session - Design Lock

### Goals

- Confirm scope and assumptions.
- Create the Django project skeleton.
- Make the app run locally and in Docker.

### Tasks

- Create Django project and apps.
- Add `requirements.txt` with Django, psycopg, python-dotenv or django-environ, and groq.
- Add Dockerfile, Docker Compose, and entrypoint.
- Configure PostgreSQL settings from environment variables.
- Create `.env.example`.
- Add base template with Bootstrap.
- Define user roles and login redirect behavior.

### Exit Criteria

- `docker compose up --build` starts Django and PostgreSQL.
- Migrations run automatically.
- Homepage redirects authenticated users by role.
- README has initial run instructions.

## Day 1 - Data Model, Auth, And Seed Foundation

### Goals

- Establish the database model and seeded users needed for all workflows.

### Tasks

- Implement `UserProfile`.
- Implement `ServicePlan`, `CustomerAccount`, `AccountUsage`, and `Payment`.
- Implement `NetworkOutage`.
- Implement `Complaint`, `ComplaintNote`, and `ComplaintStatusHistory`.
- Register useful models in Django admin.
- Create idempotent `seed_data` management command.
- Seed:
  - 5 customers.
  - 3 agents.
  - 1 admin.
  - 3 service plans.
  - Usage and payment records.
  - 2 active/inactive outages.
  - 15 complaints across categories/statuses/agents.
- Wire seed command into startup.

### Exit Criteria

- Fresh Docker startup creates all required seed data.
- Seeded login credentials are documented.
- Admin can inspect records in Django admin.
- Test data supports dashboard and chatbot scenarios.

## Day 2 - Complaint Workflows

### Goals

- Complete the core Complaint and Fault Management System.

### Tasks

- Build customer complaint list/detail/create views.
- Build agent assigned complaint queue.
- Implement workflow service for status changes.
- Build agent status update, note, and escalation forms.
- Build admin complaint list/detail views.
- Build admin assignment and status override forms.
- Add server-side permission checks.
- Add flash messages and form validation.
- Add status history creation for every status change.
- Set `resolved_at` when complaints become resolved.

### Exit Criteria

- Customer can submit and track complaints.
- Agent can work assigned complaints.
- Admin can see all complaints and assign/update them.
- Invalid role access is blocked.
- Workflow restrictions are enforced server-side.

## Day 3 - Dashboard And Chatbot

### Goals

- Implement assessment differentiators: dashboard metrics and grounded AI chatbot.

### Dashboard Tasks

- Build dashboard query service.
- Add counts by status.
- Add counts by category.
- Add average resolution time.
- Add SLA breach list for complaints older than 5 days and not resolved/closed.
- Build Bootstrap dashboard page.
- Link dashboard rows/cards to complaint details or filtered lists where practical.

### Chatbot Tasks

- Implement `ChatSession` and `ChatMessage`.
- Build customer chat page.
- Add message endpoint.
- Implement rule-based intent detection.
- Implement customer-scoped context builders.
- Integrate Groq using `GROQ_API_KEY`.
- Add strict prompt instructions.
- Store user and assistant messages.
- Add suggested question buttons.

### Exit Criteria

- Admin dashboard shows all required metrics from database queries.
- Customer chatbot answers all example question types.
- Chatbot refuses unsupported or insufficient-context questions.
- Chatbot does not expose internal notes or unrelated customer data.

## Day 4 Or Final Polish - Verification And Submission

### Goals

- Make the project reviewer-ready.

### Tasks

- Run through all role workflows from a clean Docker volume.
- Confirm first startup runs migrations and seeding automatically.
- Improve empty states and validation messages.
- Complete README.
- Add screenshots only if helpful and time permits.
- Prepare AI usage document if applicable.
- Check `.gitignore` excludes `.env`, database files, caches, and virtual environments.
- Review commit history and final repository state.

### Exit Criteria

- Reviewer can run with `docker compose up --build`.
- App is available at `http://localhost:8000`.
- Default credentials work.
- README explains chatbot setup and `.env`.
- No secrets are committed.

## Implementation Order By Dependency

1. Docker and settings.
2. Accounts and roles.
3. Customer account data.
4. Complaint models.
5. Seed command.
6. Customer complaint views.
7. Agent complaint views.
8. Admin complaint views.
9. Dashboard service and page.
10. Chat models.
11. Intent detection and context builders.
12. Groq integration.
13. README and final verification.

## Suggested File-Level Work Plan

### Foundation

Create or update:

```text
requirements.txt
Dockerfile
docker-compose.yml
entrypoint.sh
.env.example
config/settings.py
config/urls.py
templates/base.html
```

### Accounts

Create or update:

```text
accounts/models.py
accounts/decorators.py
accounts/views.py
accounts/urls.py
accounts/admin.py
accounts/templates/accounts/login.html
```

### Customer Data

Create or update:

```text
customers/models.py
customers/admin.py
customers/services.py
```

### Complaints

Create or update:

```text
complaints/models.py
complaints/forms.py
complaints/services.py
complaints/views.py
complaints/urls.py
complaints/admin.py
complaints/templates/complaints/
```

### Dashboard

Create or update:

```text
dashboard/services.py
dashboard/views.py
dashboard/urls.py
dashboard/templates/dashboard/admin_dashboard.html
```

### Chatbot

Create or update:

```text
chatbot/models.py
chatbot/intents.py
chatbot/context.py
chatbot/groq_client.py
chatbot/views.py
chatbot/urls.py
chatbot/templates/chatbot/chat.html
```

### Seed Data

Create or update:

```text
core/management/commands/seed_data.py
```

If no `core` app exists, use a `management/commands` package inside one existing app such as `customers` or create a small `core` app for cross-domain commands.

## Manual Verification Script

### Fresh Run

1. Copy `.env.example` to `.env`.
2. Fill in database password, Django secret key, and `GROQ_API_KEY`.
3. Run `docker compose up --build`.
4. Open `http://localhost:8000`.
5. Log in as admin, agent, and customer in separate sessions or sequentially.

### Customer Checks

1. Log in as seeded customer.
2. View account landing page.
3. Submit a billing or network complaint.
4. Confirm complaint starts as `Open`.
5. Confirm complaint appears in complaint history.
6. Open chatbot and ask all supported sample questions.

### Agent Checks

1. Log in as seeded agent.
2. View assigned queue sorted by age.
3. Open assigned complaint.
4. Add internal note.
5. Move status forward.
6. Escalate complaint with reason.
7. Confirm unassigned complaints are inaccessible.

### Admin Checks

1. Log in as seeded admin.
2. View dashboard.
3. Confirm counts by status/category.
4. Confirm average resolution time is shown.
5. Confirm SLA breach list appears.
6. Assign a complaint to another agent.
7. Override complaint status.

## README Checklist

The README should include:

- Project overview.
- Stack summary.
- Prerequisites.
- Environment variable setup.
- Run instructions.
- Automatic migration and seeding explanation.
- Default login credentials.
- Chatbot setup with Groq.
- Assumptions and design decisions.
- Manual test checklist.
- Troubleshooting notes.

Example credentials section:

```text
Admin:
  username: admin
  password: AdminPass123!

Agents:
  username: agent1
  password: AgentPass123!

Customers:
  username: customer1
  password: CustomerPass123!
```

Use deterministic credentials only for seeded demo users and clearly state they are for assessment use.

## Risk Register

### Docker Startup Complexity

Risk:

- Migrations or seeding may run before PostgreSQL is ready.

Mitigation:

- Add a wait loop in `entrypoint.sh`.
- Keep seed command idempotent.

### Chatbot Hallucination

Risk:

- LLM may answer beyond context.

Mitigation:

- Use deterministic context.
- Use strict prompt.
- Use low temperature.
- Return direct fallback when intent is unsupported.

### Role Leakage

Risk:

- Customers may access internal notes or other customer complaints.

Mitigation:

- Scope querysets by role and owner.
- Do not pass internal notes to templates or chatbot context.
- Add manual permission tests.

### Time Overrun

Risk:

- Too much time spent on UI polish or custom admin screens.

Mitigation:

- Use Bootstrap templates.
- Use Django admin for lower-priority internal management.
- Prioritize required workflows first.

## Nice-To-Haves Only After Core Completion

- Filterable complaint tables.
- Pagination.
- Simple chart styling for dashboard metrics.
- Chat session list/history sidebar.
- Admin outage management page.
- Basic automated tests for workflow service.

These should not block the required assessment features.
