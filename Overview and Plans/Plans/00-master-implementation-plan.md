# Master Implementation Plan

## Purpose

This is the high-level delivery plan for the Telecom Customer Portal technical assessment. It consolidates project-wide scope, sequencing, seed data, verification, README, submission, and risk planning. Detailed implementation steps live in the three module plans:

1. `01-system-architecture-plan.md` - project foundation, PostgreSQL, Docker, auth, roles, base UI, and shared customer account data.
2. `02-complaint-and-fault-management-plan.md` - complaint workflow, fault/outage records, agent/admin/customer complaint flows, SLA, and dashboard.
3. `03-ai-customer-chatbot-plan.md` - chat sessions, deterministic intent handling, customer-scoped context, Groq integration, and chat UI.

The plans are intentionally ordered. Build `01` first, then `02`, then `03`.

## Project Overview

Build a small but complete telecom customer portal with two core modules:

- Complaint and Fault Management System: customers submit and track complaints, agents manage assigned work, and admins assign, override, and report on complaint activity.
- AI Customer Chatbot: logged-in customers ask account questions and receive answers grounded in database records.

The assessment should demonstrate strong Django fundamentals, clean database design, pragmatic scoping, Docker-based setup, readable documentation, and a coherent reviewer experience.

## Full System Scope

In scope:

- Django project with PostgreSQL.
- Docker Compose startup using `docker compose up --build`.
- Environment-based configuration.
- Automatic migrations on container startup.
- Automatic first-run seed data.
- Django authentication.
- Customer, Agent, and Admin roles.
- Role-based redirects and access control.
- Customer account, plan, usage, and payment records.
- Complaint creation, history, detail, assignment, notes, workflow, escalation, and status history.
- Admin dashboard with required metrics.
- Network outage/fault records tied to regions.
- Chatbot using Groq `llama-3.1-8b-instant`.
- README with setup, credentials, chatbot, seed, assumptions, and run instructions.

Out of scope:

- External auth providers.
- Supabase.
- Microservices.
- Vector databases, RAG, embeddings, or autonomous SQL.
- Production-grade telecom integrations.
- Production-grade observability or deployment.

## Technology Stack

- Backend: Python 3.x, Django.
- Database: PostgreSQL.
- Frontend: Django templates with Bootstrap.
- Containerization: Docker and Docker Compose.
- LLM: Groq Python SDK using `llama-3.1-8b-instant`.
- Version control: GitHub or Bitbucket.

Use Django templates with Bootstrap instead of React. The required UI is mostly forms, tables, dashboard cards, and a chat page, so server-rendered templates keep the implementation focused and explainable.

## Overall Architecture Summary

Use a modular Django monolith:

```text
Browser
  |
  v
Django web container
  |
  v
PostgreSQL db container

Django web container
  |
  v
Groq API, chatbot only
```

Recommended apps:

- `accounts`: profiles, roles, auth helpers, role redirects.
- `customers`: service plans, customer accounts, usage, payments.
- `complaints`: complaints, notes, workflow, status history.
- `network`: outage/fault records.
- `dashboard`: admin complaint metrics.
- `chatbot`: chat sessions, messages, intent detection, context, Groq.
- `core`: optional shared management commands such as `seed_data`.

Request flow:

1. User logs in with Django auth.
2. Role redirect sends the user to the right landing page.
3. Views enforce role checks and scoped querysets.
4. Forms validate user input.
5. Services enforce workflow, SLA, dashboard, and chatbot business logic.
6. Templates render role-specific Bootstrap pages.

## Global Assumptions

- Seeded users are enough; customer self-registration is not required.
- One customer has one active telecom account.
- A customer account has one active service plan.
- Monthly usage is stored as aggregate data, not calculated from real telecom events.
- Payments are seeded records used for display and chatbot responses.
- Network outages are seeded or admin-managed records, not pulled from an external system.
- Django admin may be used for lower-priority internal management.
- SLA threshold is 5 days from complaint creation while not resolved or closed.
- Chatbot factual answers must come from deterministic database queries.

## Cross-Cutting Decisions

- Use Django's built-in `User` plus `UserProfile` instead of a custom user model to reduce assessment risk.
- Keep authorization in decorators/mixins, view querysets, and service validation, not only in templates.
- Use service functions for workflow transitions, dashboard metrics, chatbot context, and Groq calls.
- Store `resolved_at` on complaints to simplify average resolution calculations.
- Use idempotent seed data so Docker startup is predictable.
- Do not commit `.env` or any real API keys.

## Overall Implementation Order

1. Create Django project, Docker, PostgreSQL settings, and environment configuration.
2. Implement auth foundation: `UserProfile`, role helpers, login/logout, role redirects, base templates.
3. Implement shared customer account data: plans, accounts, usage, payments.
4. Implement complaint and outage models.
5. Implement seed command and startup seeding.
6. Implement customer complaint create/list/detail.
7. Implement agent queue, notes, status updates, and escalation.
8. Implement admin complaint management and dashboard.
9. Implement chatbot session/message models.
10. Implement intent detection and customer-scoped context builders.
11. Integrate Groq and prompt guardrails.
12. Complete README, manual verification, and submission prep.

## 3-4 Day Delivery Timeline

### Day 0 Or Start Session - Foundation

Goals:

- Create the Django skeleton.
- Make Docker and PostgreSQL work.
- Establish authentication and role structure.

Tasks:

- Create `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `entrypoint.sh`, `.env.example`.
- Configure Django settings from environment variables.
- Create `accounts`, `customers`, and placeholder module apps.
- Add `UserProfile`.
- Add login/logout and role redirect.
- Add Bootstrap base layout.

Exit criteria:

- `docker compose up --build` starts the app and database.
- Migrations run automatically.
- Login works.
- Users can be redirected by role once seeded.

### Day 1 - Data And Seeding

Goals:

- Build the database foundation and demo data.

Tasks:

- Implement customer account, plan, usage, payment, complaint, and outage models.
- Register useful models in Django admin.
- Implement idempotent `seed_data --if-empty`.
- Seed 5 customers, 3 agents, 1 admin, 3 plans, payments, usage, 15 complaints, and 2 outages.
- Wire seed command into `entrypoint.sh`.

Exit criteria:

- Fresh startup creates all required seed data.
- Default credentials are documented.
- Admin can inspect seed data.

### Day 2 - Complaint And Fault Module

Goals:

- Complete customer, agent, and admin complaint workflows.

Tasks:

- Build customer complaint list, detail, and create pages.
- Build agent assigned queue and detail page.
- Add workflow, note, and escalation forms.
- Build admin complaint list/detail, assignment, and status override.
- Add workflow service, status history, and `resolved_at` handling.
- Add SLA and dashboard query services.

Exit criteria:

- Customers can submit and track complaints.
- Agents can work assigned complaints.
- Admins can assign, override, and view metrics.
- Permission checks block invalid role access.

### Day 3 - Dashboard And Chatbot

Goals:

- Finish assessment differentiators.

Tasks:

- Build admin dashboard page.
- Implement chat sessions and messages.
- Add deterministic intent detection.
- Add context builders for plan, balance, usage, complaints, payments, and outages.
- Integrate Groq with strict prompt instructions.
- Build chat UI with suggested questions.

Exit criteria:

- Dashboard shows all required metrics.
- Chatbot answers all example questions from database context.
- Chatbot refuses unsupported or insufficient-context questions.

### Day 4 Or Final Polish

Goals:

- Make the project reviewer-ready.

Tasks:

- Run the full manual verification checklist.
- Improve empty states and validation messages.
- Complete README.
- Confirm `.gitignore` protects secrets and local artifacts.
- Prepare AI usage document if applicable.
- Review final repository state.

Exit criteria:

- Reviewer can run the project from a clean clone with the README.
- App is available at `http://localhost:8000`.
- Default credentials work.
- No secrets are committed.

## Seed Data Strategy Summary

Create a management command:

```bash
python manage.py seed_data --if-empty
```

Startup flow:

```bash
python manage.py migrate --noinput
python manage.py seed_data --if-empty
python manage.py runserver 0.0.0.0:8000
```

Seed command rules:

- If users or customer accounts already exist, skip normal seed.
- Use deterministic usernames and `get_or_create`.
- Never overwrite reviewer-created data during normal startup.
- Print a concise created/skipped summary.

Required seed data:

- 5 customer users and accounts.
- 3 agent users.
- 1 admin user.
- 3 service plans.
- Current usage and at least one payment per customer.
- 15 complaints across statuses, categories, ages, and agents.
- At least 2 network outage/fault records tied to regions.
- At least 2 unresolved complaints old enough to breach SLA.

Suggested default credentials:

```text
Admin:
  admin / AdminPass123!

Agents:
  agent1 / AgentPass123!
  agent2 / AgentPass123!
  agent3 / AgentPass123!

Customers:
  customer1 / CustomerPass123!
  customer2 / CustomerPass123!
  customer3 / CustomerPass123!
  customer4 / CustomerPass123!
  customer5 / CustomerPass123!
```

Suggested service plans:

| Plan | Price | Data | Minutes | SMS |
|---|---:|---:|---:|---:|
| Basic | 25.00 | 5 GB | 300 | 100 |
| Standard | 40.00 | 20 GB | 1000 | 500 |
| Premium | 55.00 | 50 GB | 2000 | 1000 |

Suggested regions:

- Kingston.
- Montego Bay.
- Spanish Town.
- Portmore.
- Ocho Rios.

## README And Submission Checklist

Root `README.md` should include:

- Project overview.
- Technology stack.
- Prerequisites: Docker, Docker Compose, Groq API key.
- Environment setup with all variables from `.env.example`.
- First run: `docker compose up --build`.
- Subsequent run: `docker compose up`.
- Automatic migration and seed behavior.
- Default login credentials.
- Chatbot setup and `GROQ_API_KEY`.
- Assumptions and design decisions.
- Manual test checklist.
- Troubleshooting notes.

Security requirements:

- Include `.env.example`.
- Do not commit `.env`.
- Do not commit real `GROQ_API_KEY`.
- Ensure `.gitignore` excludes local env files, virtual environments, cache files, and database artifacts.

Final submission:

- Public GitHub or Bitbucket repository link.
- `.env` contents sent separately as the required text attachment, including working `GROQ_API_KEY`.
- AI usage document if applicable.
- Commit history preserved.

## Manual Verification Checklist

Fresh startup:

1. Copy `.env.example` to `.env`.
2. Fill in database variables, `DJANGO_SECRET_KEY`, and `GROQ_API_KEY`.
3. Run `docker compose up --build`.
4. Open `http://localhost:8000`.
5. Confirm migrations and seed data ran automatically.

Customer checks:

1. Log in as `customer1`.
2. View account summary.
3. Submit a complaint.
4. Confirm complaint starts as `Open`.
5. Confirm complaint appears in history.
6. Confirm customer cannot access agent/admin URLs.
7. Ask chatbot all supported sample questions.

Agent checks:

1. Log in as `agent1`.
2. View assigned queue sorted by age.
3. Open an assigned complaint.
4. Add internal note.
5. Move status forward.
6. Escalate with reason.
7. Confirm unassigned complaints are inaccessible.

Admin checks:

1. Log in as `admin`.
2. View dashboard.
3. Confirm counts by status and category.
4. Confirm average resolution time appears.
5. Confirm SLA breach list appears.
6. Assign or reassign a complaint.
7. Override complaint status.

Chatbot checks:

1. Ask "What plan am I currently on?"
2. Ask "What is my current account balance?"
3. Ask "How much data have I used this month?"
4. Ask "Do I have any open complaints?"
5. Ask "When was my last payment made?"
6. Ask "Are there any active faults or outages affecting my area?"
7. Ask an unsupported question and confirm it refuses to fabricate.

## Risk Register

### Docker Startup Timing

Risk:

- Migrations or seeding may run before PostgreSQL is ready.

Mitigation:

- Add a PostgreSQL wait loop in `entrypoint.sh`.
- Keep seed command idempotent.

### Role Leakage

Risk:

- Customers may see internal notes or other customers' records.

Mitigation:

- Scope querysets by role and owner.
- Enforce role decorators on all module routes.
- Never pass internal notes into customer templates or chatbot context.

### Workflow Drift

Risk:

- Status rules may be implemented inconsistently across views.

Mitigation:

- Use one complaint workflow service.
- Ensure every status update writes history.

### Chatbot Hallucination

Risk:

- The LLM may answer beyond the provided context.

Mitigation:

- Use rule-based intent detection.
- Query deterministic, customer-scoped data.
- Use strict system prompt and low temperature.
- Return direct fallback for unsupported or missing-context questions.

### Time Overrun

Risk:

- Too much time spent on custom admin tools or UI polish.

Mitigation:

- Use Django admin for lower-priority internal management.
- Use Bootstrap templates.
- Prioritize required workflows and reviewer run experience.

## Nice-To-Haves After Core Completion

- Filterable and paginated complaint tables.
- Simple dashboard charts.
- Chat history sidebar.
- Custom admin outage management page.
- Automated tests for workflow and permission services.

These should not block required assessment functionality.

## Assessment Success Criteria

The finished project should show:

- A reviewer can run the app with one Docker Compose command.
- Each role has a clear workflow.
- Complaint workflow rules are enforced server-side.
- Dashboard metrics come from real database queries.
- Chatbot answers use seeded database facts only.
- The code is conventional Django and easy to explain in an interview.
