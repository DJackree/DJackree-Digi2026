# Master Implementation Plan

## Purpose

This plan translates `Project Overview/ProjectDescription.md` into an execution-ready approach for a 3-4 day take-home assessment. The goal is to build a small, complete telecom customer portal using Django, PostgreSQL, Docker Compose, Django templates with Bootstrap, and the Groq API.

The implementation should optimize for correctness, clarity, reviewer experience, and explainable engineering decisions. It should avoid production-scale complexity, external authentication providers, microservices, vector databases, and advanced AI pipelines.

## Product Scope

The application has two primary modules:

- Complaint and Fault Management System: customers submit complaints, agents work assigned complaints, and admins manage assignments, workflow, users, and reporting.
- AI Customer Chatbot: logged-in customers ask account questions and receive answers based only on database-backed context passed to Groq.

Supporting capabilities:

- Role-based authentication and authorization.
- Seeded telecom sample data.
- Admin dashboard metrics.
- Automatic migrations and seeding on Docker startup.
- README and assessment submission documentation.

## Recommended Stack

- Backend: Python 3.x, Django.
- Database: PostgreSQL.
- Frontend: Django templates with Bootstrap.
- LLM: Groq Python SDK using `llama-3.1-8b-instant`.
- Runtime: Docker and Docker Compose.

Use Django templates instead of React for this assessment. The UI requirements are form, table, dashboard, and chat workflows that can be delivered quickly with server-rendered pages. This keeps time focused on backend design, workflow rules, data modeling, and reviewer usability.

## Global Architecture

### Services

Use a simple Docker Compose setup:

- `web`: Django application container.
- `db`: PostgreSQL container.

Optional local-only supporting files:

- `.env.example`: documents required environment variables without secrets.
- `entrypoint.sh`: waits for PostgreSQL, runs migrations, seeds if needed, starts Django.

### Django Project Structure

Recommended apps:

- `accounts`: custom user profile and role support.
- `customers`: customer accounts, plans, balances, usage, payments.
- `complaints`: complaint categories, workflow, assignments, notes, SLA logic.
- `network`: outage/fault records by region.
- `chatbot`: chat sessions, chat messages, intent detection, Groq integration.
- `dashboard`: admin metrics and reporting views.

This is enough separation to keep domains clear without overengineering.

### High-Level Request Flow

1. User authenticates using Django auth.
2. Role middleware or view mixins route users to role-specific screens.
3. Views enforce permissions before reading or mutating records.
4. Forms validate request data and business rules.
5. Services handle workflow, dashboard calculations, chatbot context construction, and Groq calls.
6. Templates render Bootstrap pages with clear role-specific actions.

## Authentication And Authorization Strategy

Use Django's built-in auth system with a profile model to store role and telecom-specific metadata.

Roles:

- Customer: can view and edit only their own customer-facing records where allowed.
- Agent: can view complaints assigned to them and update workflow fields allowed for agents.
- Admin: can view and manage all records, assign complaints, manage users, and view reports.

Recommended model approach:

```python
class UserProfile(models.Model):
    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        AGENT = "agent", "Agent"
        ADMIN = "admin", "Admin"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=Role.choices)
    region = models.CharField(max_length=100, blank=True)
```

Authorization should be enforced in:

- URL access: decorators or class-based view mixins.
- Querysets: filter records by current user's role.
- Forms/services: validate state transitions and ownership.
- Templates: hide actions the role cannot perform.

Do not rely only on hiding buttons in the UI.

## Core Data Model

Core entities:

- User and UserProfile.
- CustomerAccount.
- ServicePlan.
- AccountUsage.
- Payment.
- Complaint.
- ComplaintNote.
- ComplaintStatusHistory.
- NetworkOutage.
- ChatSession.
- ChatMessage.

Key relationships:

- UserProfile extends Django User.
- CustomerAccount belongs to a customer user and a ServicePlan.
- Complaints belong to a CustomerAccount and may be assigned to an agent user.
- ComplaintNote belongs to a Complaint and author user.
- ComplaintStatusHistory records status transitions for auditability and resolution metrics.
- ChatSession belongs to a customer user.
- ChatMessage belongs to a ChatSession.
- NetworkOutage is tied to a region.

Normalize data where it improves query clarity: plans, payments, usage, complaints, and outages should be separate tables. Avoid unnecessary abstractions such as generic event tables.

## Critical Business Rules

### Complaint Workflow

Required lifecycle:

```text
Open -> In Progress -> Escalated -> Resolved -> Closed
```

Agent rules:

- Agents can update only complaints assigned to them.
- Agents can move complaints forward through the workflow.
- Agents can flag complaints for escalation and must provide an escalation reason.
- Agents can add internal or resolution notes.

Admin rules:

- Admins can see all complaints.
- Admins can assign and reassign complaints.
- Admins can move complaints to any status.
- Admins can manage users through Django admin or a basic internal UI.

Customer rules:

- Customers can create complaints for their own account.
- Customers can view only their own complaints.
- Customers cannot update status, assigned agent, or internal notes.
- Customers should not see internal notes.

### SLA Logic

Use a simple SLA threshold of 5 days from complaint submission while status is not `resolved` or `closed`.

SLA breach condition:

```text
created_at < now - 5 days AND status NOT IN (Resolved, Closed)
```

Average resolution time:

```text
resolved_at - created_at
```

Store `resolved_at` when a complaint first enters `Resolved`. This avoids recalculating from status history during dashboard rendering.

### Chatbot Logic

The chatbot must be deterministic around data retrieval and conservative around generation.

Flow:

1. Detect intent using keyword/rule matching.
2. Query only the current customer's relevant database records.
3. Build a minimal context object.
4. Send the context and the user's question to Groq.
5. Instruct the model to answer only from context.
6. Store chat messages in the current session.

No RAG, vector database, document embeddings, or autonomous SQL generation should be used.

## API And Route Surface

Because Django templates are recommended, most routes can be server-rendered pages. Add small JSON endpoints only where they simplify chat and dashboard interactions.

Major route groups:

- Auth: login, logout, role-aware redirect.
- Customer complaints: list, detail, create.
- Agent complaints: assigned list, update status, add note, escalate.
- Admin complaints: all complaints, assign, update status.
- Dashboard: admin metrics page.
- Chatbot: chat page and message endpoint.

Detailed endpoint plans are documented in the module-specific plan files.

## Seed Data Strategy

Create a Django management command:

```bash
python manage.py seed_data
```

The Docker entrypoint should run:

1. `python manage.py migrate`
2. `python manage.py seed_data --if-empty`
3. `python manage.py runserver 0.0.0.0:8000`

The seed command should be idempotent. It should check whether users or customer accounts already exist and skip creating duplicates.

Required seed data:

- 5 customer accounts.
- 3 agent accounts.
- 1 admin account.
- 15 complaints across statuses, categories, and agents.
- 3 service plans.
- 2 network outages tied to regions.
- Usage, balance, and payment records for chatbot answers.

## Development Phases

### Phase 0 - Design

- Finalize model fields, roles, and status transition rules.
- Create wireframe-level page list.
- Decide seed credentials.
- Document assumptions in `README.md`.

### Phase 1 - Foundation

- Create Django project and apps.
- Configure PostgreSQL and environment variables.
- Add Dockerfile, Docker Compose, and entrypoint.
- Configure Bootstrap base template.
- Implement authentication and role-aware redirects.

### Phase 2 - Core Complaint Features

- Implement complaint models, migrations, forms, and views.
- Build customer complaint create/list/detail pages.
- Build agent assigned complaint view and status update flow.
- Build admin assignment and full complaint management flow.

### Phase 3 - Business Logic And Dashboard

- Implement workflow validation service.
- Implement SLA breach detection.
- Add complaint status history and resolution timestamp handling.
- Build admin dashboard metrics.

### Phase 4 - Customer Data And Seed Automation

- Implement plans, accounts, usage, payments, and outages.
- Build idempotent seed command.
- Wire seed command into Docker startup.
- Verify seeded credentials and sample workflows.

### Phase 5 - Chatbot

- Implement chat session and message models.
- Implement intent detection.
- Implement context builders for account plan, balance, usage, complaints, payments, and outages.
- Integrate Groq using environment variables.
- Build chat UI and message endpoint.
- Add prompt guardrails to prevent hallucination.

### Phase 6 - Polish And Submission

- Complete README.
- Add `.env.example`.
- Verify `docker compose up --build` works from a clean state.
- Run manual role-based test scripts.
- Prepare AI usage document if applicable.

## Assumptions

- Customer accounts are prepaid or postpaid records stored in the app, not integrated with a real telecom billing system.
- A customer has one active service plan for this assessment.
- Usage data is monthly aggregate data, not a live metering feed.
- Network outages are manually seeded static records.
- Django templates with Bootstrap are sufficient for the required UI.
- Django admin may support internal user management, while custom pages cover assessment-specific workflows.
- The chatbot is allowed to use the LLM for wording, but all factual data must come from deterministic database queries.
- Conversation history is scoped to the user's current authenticated session and stored in the database.

## Key Design Tradeoffs

- Django templates over React: faster delivery, fewer moving parts, strong fit for form-based workflows.
- Profile model over custom user model: simpler for a short assessment, while still supporting roles.
- Service functions for workflow and chatbot context: keeps business rules testable and avoids burying logic in views.
- Stored `resolved_at`: improves dashboard simplicity and makes average resolution time explicit.
- Rule-based chatbot intent detection: meets requirements while preventing unsafe open-ended data access.

## Assessment Success Criteria

The finished project should demonstrate:

- A reviewer can run the app with one Docker Compose command.
- Each role has a clear and usable path through the application.
- Complaint workflow rules are enforced server-side.
- Dashboard numbers come from real database queries.
- The chatbot answers using seeded database facts and refuses unsupported questions.
- The codebase is readable, conventional Django, and easy to explain in an interview.
