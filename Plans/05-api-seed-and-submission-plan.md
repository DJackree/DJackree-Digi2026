# API, Seed Data, And Submission Plan

## Purpose

This plan centralizes the endpoint surface, seed data requirements, README content, and final submission checks for the assessment.

Although the recommended implementation uses Django templates, documenting the route surface makes the system easier to build, test, and explain.

## Route Surface

### Authentication And Landing

| Method | URL | Purpose | Access |
|---|---|---|---|
| GET | `/` | Redirect authenticated users to role landing page | Authenticated |
| GET/POST | `/accounts/login/` | Login | Anonymous |
| POST | `/accounts/logout/` | Logout | Authenticated |

Behavior:

- Customer redirects to customer dashboard.
- Agent redirects to agent complaint queue.
- Admin redirects to admin dashboard.

### Customer Account

| Method | URL | Purpose | Access |
|---|---|---|---|
| GET | `/customer/` | Customer landing/account summary | Customer |
| GET | `/customer/account/` | Account details, plan, balance, usage | Customer |

Data shown:

- Account number.
- Current plan.
- Current balance.
- Monthly usage.
- Last payment summary.

### Customer Complaints

| Method | URL | Purpose | Access |
|---|---|---|---|
| GET | `/complaints/` | Own complaint history | Customer |
| GET | `/complaints/new/` | New complaint form | Customer |
| POST | `/complaints/new/` | Create complaint | Customer |
| GET | `/complaints/<reference>/` | Own complaint detail | Customer |

Create form fields:

```json
{
  "category": "billing",
  "description": "I was charged twice for my monthly plan."
}
```

Response behavior:

- On success, redirect to detail page and show success message.
- On validation error, re-render form with errors.

### Agent Complaints

| Method | URL | Purpose | Access |
|---|---|---|---|
| GET | `/agent/complaints/` | Assigned queue | Agent |
| GET | `/agent/complaints/<reference>/` | Assigned complaint detail | Agent |
| POST | `/agent/complaints/<reference>/status/` | Move status forward | Agent |
| POST | `/agent/complaints/<reference>/notes/` | Add internal note | Agent |
| POST | `/agent/complaints/<reference>/escalate/` | Escalate with reason | Agent |

Status update form fields:

```json
{
  "status": "in_progress",
  "note": "Reviewed customer account and started investigation."
}
```

Escalation form fields:

```json
{
  "reason": "Issue appears related to a wider regional network fault."
}
```

### Admin Dashboard And Complaints

| Method | URL | Purpose | Access |
|---|---|---|---|
| GET | `/admin-portal/dashboard/` | Metrics dashboard | Admin |
| GET | `/admin-portal/complaints/` | All complaints | Admin |
| GET | `/admin-portal/complaints/<reference>/` | Complaint detail | Admin |
| POST | `/admin-portal/complaints/<reference>/assign/` | Assign/reassign agent | Admin |
| POST | `/admin-portal/complaints/<reference>/status/` | Override status | Admin |

Assignment form fields:

```json
{
  "agent_id": 12
}
```

Dashboard metrics response shape if implemented as a JSON helper:

```json
{
  "by_status": {
    "open": 5,
    "in_progress": 4,
    "escalated": 2,
    "resolved": 3,
    "closed": 1
  },
  "by_category": {
    "billing": 4,
    "network": 5,
    "device": 2,
    "roaming": 2,
    "other": 2
  },
  "average_resolution_hours": 52.5,
  "sla_breaches": []
}
```

### Chatbot

| Method | URL | Purpose | Access |
|---|---|---|---|
| GET | `/chatbot/` | Chat UI | Customer |
| POST | `/chatbot/messages/` | Send message and receive answer | Customer |
| POST | `/chatbot/sessions/new/` | Start new session | Customer |

Message request:

```json
{
  "session_id": 1,
  "message": "Do I have any open complaints?"
}
```

Message response:

```json
{
  "session_id": 1,
  "intent": "open_complaints",
  "message": "You have 2 open complaints: CMP-2026-0002 for Billing and CMP-2026-0005 for Network."
}
```

## Seed Data Plan

### Required Seed Entities

Users:

- 5 customers.
- 3 agents.
- 1 admin.

Customer data:

- 5 customer accounts.
- 3 service plans.
- Usage records for the current billing period.
- Payment records with at least one payment per customer.

Complaint data:

- At least 15 complaints.
- Distribution across statuses:
  - Open.
  - In Progress.
  - Escalated.
  - Resolved.
  - Closed.
- Distribution across categories:
  - Billing.
  - Network.
  - Device.
  - Roaming.
  - Other.
- Mix of assigned and unassigned complaints.
- At least two complaints old enough to breach SLA.

Network data:

- At least 2 simulated outage/fault records.
- At least one active outage matching a seeded customer region.

### Suggested Seed Values

Service plans:

| Plan | Price | Data | Minutes | SMS |
|---|---:|---:|---:|---:|
| Basic | 25.00 | 5 GB | 300 | 100 |
| Standard | 40.00 | 20 GB | 1000 | 500 |
| Premium | 55.00 | 50 GB | 2000 | 1000 |

Regions:

- Kingston.
- Montego Bay.
- Spanish Town.
- Portmore.
- Ocho Rios.

Default credentials:

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

These credentials are for seeded assessment/demo data only.

### Idempotent Seed Command

Command:

```bash
python manage.py seed_data --if-empty
```

Rules:

- If users or customer accounts already exist, skip full seed unless a force flag is provided.
- Use `get_or_create` for deterministic records.
- Print created/skipped counts.
- Never overwrite real user-changed data during normal startup.

Suggested command behavior:

```text
Checking database seed state...
Existing users found: skipping seed data.
```

or:

```text
Database empty. Creating seed data...
Created 9 users, 5 accounts, 15 complaints, 2 outages.
```

## README Plan

### Required Sections

Project Overview:

- Explain the two modules and role-based portal.

Prerequisites:

- Docker.
- Docker Compose.
- Groq API key.

Environment Setup:

- Explain copying `.env.example` to `.env`.
- List variables and descriptions.
- Warn not to commit `.env`.

How To Run:

```bash
docker compose up --build
```

Subsequent runs:

```bash
docker compose up
```

How Seeding Works:

- Migrations run on startup.
- Seed command runs automatically only when database is empty.
- Reviewer does not need to run manual commands.

Default Login Credentials:

- Include admin, agent, and customer credentials.

Chatbot Setup:

- Explain `GROQ_API_KEY`.
- Confirm model: `llama-3.1-8b-instant`.
- Mention chatbot answers only from database context.

Assumptions And Design Decisions:

- Django templates selected for speed and simplicity.
- Rule-based intent detection selected to keep data access safe.
- SLA threshold set to 5 days.
- Django admin used for lower-priority internal management where appropriate.

Manual Test Checklist:

- Include short role-by-role verification steps.

## Security And Secret Handling

Repository should include:

- `.env.example`
- `.gitignore`
- README variable documentation.

Repository should not include:

- `.env`
- real `GROQ_API_KEY`
- database volume files
- Python cache files
- local virtual environments

Submission requires an `.env` file as a separate plain text attachment, per assessment instructions. Keep it outside version control.

## Final Submission Checklist

Before submitting:

- Fresh clone instructions in README are accurate.
- `docker compose up --build` works with a configured `.env`.
- App opens at `http://localhost:8000`.
- Migrations run automatically.
- Seed data runs automatically on first startup.
- Default credentials work.
- Customer can submit and track complaint.
- Agent can update assigned complaint.
- Admin can assign complaints and view dashboard.
- Chatbot answers all example questions from seeded data.
- Chatbot refuses unsupported questions.
- No secrets are committed.
- AI usage document is prepared if applicable.
- Public GitHub or Bitbucket repository link is ready.
- `.env` values are copied into the required `env_config.txt` attachment for submission.

## Interview Readiness Notes

Be ready to explain:

- Why Django templates were chosen over React.
- How role checks are enforced beyond the UI.
- How complaint workflow rules are centralized.
- How SLA breaches and average resolution time are calculated.
- How chatbot context is selected.
- How hallucination is reduced.
- How Docker startup handles migrations and seeding.
- What would be improved with more time.
