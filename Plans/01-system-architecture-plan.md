# System Architecture Plan

## Purpose

This plan defines the technical foundation for the telecom customer portal. It covers project structure, containerization, configuration, authentication, shared data modeling, startup behavior, and reviewer-facing documentation.

## Architecture Overview

Use a modular Django monolith backed by PostgreSQL. This keeps deployment simple and matches the assessment's timebox while still showing clean separation of concerns.

```text
Browser
  |
  | HTTP
  v
Django web container
  |
  | ORM
  v
PostgreSQL container

Django web container
  |
  | HTTPS API call for chatbot only
  v
Groq API
```

## Docker Compose Design

### Services

`web`:

- Builds the Django app image.
- Reads configuration from `.env`.
- Waits for PostgreSQL.
- Runs migrations.
- Runs seed command if data is missing.
- Starts Django at `0.0.0.0:8000`.

`db`:

- Runs PostgreSQL.
- Uses a named volume for persistence.
- Reads database name, user, and password from `.env`.

### Expected Files

```text
Dockerfile
docker-compose.yml
entrypoint.sh
.env.example
requirements.txt
manage.py
config/
accounts/
customers/
complaints/
network/
chatbot/
dashboard/
templates/
static/
```

### Environment Variables

Document these in `.env.example` and `README.md`:

```text
DJANGO_SECRET_KEY=
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
POSTGRES_DB=telecom_portal
POSTGRES_USER=telecom_user
POSTGRES_PASSWORD=
POSTGRES_HOST=db
POSTGRES_PORT=5432
GROQ_API_KEY=
```

Do not commit `.env`.

## Django App Responsibilities

### `accounts`

Responsibilities:

- User profile and role storage.
- Role helpers and decorators.
- Login/logout templates.
- Role-based redirect after login.

### `customers`

Responsibilities:

- Customer account records.
- Service plans.
- Usage summaries.
- Payments.
- Customer-facing account context used by chatbot.

### `complaints`

Responsibilities:

- Complaint records.
- Complaint notes.
- Status history.
- Workflow validation.
- Customer, agent, and admin complaint views.

### `network`

Responsibilities:

- Network outage/fault records.
- Region-based active outage lookup for chatbot.

### `chatbot`

Responsibilities:

- Chat sessions and messages.
- Intent detection.
- Context building.
- Groq service wrapper.
- Chat UI and message endpoint.

### `dashboard`

Responsibilities:

- Admin dashboard queries.
- SLA breach reporting.
- Summary metric views.

## Phase 0 - Design

### Purpose

Define the architectural boundaries and shared conventions before implementation.

### Entities And Relationships

Shared entities:

- `User`: Django built-in user.
- `UserProfile`: one-to-one with `User`, stores role and optional region.
- `CustomerAccount`: one-to-one or foreign key to `User`, stores telecom account data.
- `ServicePlan`: referenced by `CustomerAccount`.
- `Complaint`: references `CustomerAccount` and optional agent `User`.
- `ChatSession`: references customer `User`.

### Business Rules And Constraints

- Every authenticated user must have exactly one profile.
- Every customer user should have exactly one customer account in seed data.
- Agent and admin users should not have customer account records unless explicitly needed later.
- Role checks must be enforced in views and querysets.
- All user-facing write operations should use Django forms or explicit validation services.

### Ambiguities And Assumptions

- The assessment does not require customer self-registration, so seed users and admin-created users are enough.
- Django admin can satisfy "manage users" unless time allows a custom admin user management page.
- One customer account per customer is enough for the assessment.

### Design Decisions

- Use Django's built-in `User` rather than a custom user model to reduce setup risk.
- Store roles in `UserProfile` because the role model is simple and unlikely to change.
- Use app-level services for workflow and chatbot logic so views remain thin.

## Phase 1 - Database

### Profile Model

```python
class UserProfile(models.Model):
    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        AGENT = "agent", "Agent"
        ADMIN = "admin", "Admin"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=Role.choices, db_index=True)
    region = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

Field rationale:

- `user`: links role data to Django auth.
- `role`: supports role-aware routing and permissions.
- `region`: supports outage lookup for customers and possible agent filtering.
- timestamps: useful for audit and admin inspection.

Constraints:

- One profile per user.
- Role indexed because it is used for filtering users.

### Migration Plan

1. Create apps.
2. Add profile model.
3. Add domain models in module-specific apps.
4. Run migrations automatically on startup.

## Phase 2 - API And Routes

### Auth Routes

| Method | URL | Purpose | Access |
|---|---|---|---|
| GET/POST | `/accounts/login/` | Login form | Anonymous |
| POST | `/accounts/logout/` | Logout | Authenticated |
| GET | `/` | Role-aware landing redirect | Authenticated |

### Authorization Helpers

Recommended helpers:

```python
def role_required(*roles):
    ...

def is_customer(user):
    ...

def is_agent(user):
    ...

def is_admin(user):
    ...
```

Validation strategy:

- Anonymous users redirect to login.
- Authenticated users without the required role receive HTTP 403.
- Querysets are scoped by role before objects are loaded.

Error handling:

- Use 404 for objects outside a user's allowed queryset.
- Use 403 when the user is authenticated but lacks the role entirely.
- Use form errors for invalid write attempts.

## Phase 3 - UI

### Base Layout

Pages should share a Bootstrap base template:

- Top navigation with role-specific links.
- Authenticated user's name and role.
- Flash message area.
- Main content container.

### Role Landing Pages

Customer:

- Account summary.
- Complaint history link.
- Submit complaint link.
- Chatbot link.

Agent:

- Assigned complaint queue.
- Escalation-focused task list.

Admin:

- Dashboard metrics.
- All complaints.
- User/admin management links.

### UI Behavior

- Hide actions unavailable to the current role.
- Keep forms short and clear.
- Confirm status-changing actions with explicit buttons or form labels.
- Display validation errors inline.

## Startup And Seeding Flow

The `entrypoint.sh` script should run commands in this order:

```bash
python manage.py migrate --noinput
python manage.py seed_data --if-empty
python manage.py runserver 0.0.0.0:8000
```

The seed command should:

- Check whether seed users already exist.
- Create deterministic usernames and passwords.
- Create realistic customer/account/complaint/outage data.
- Print a short summary to startup logs.

## Testing And Verification

Minimum manual checks:

- `docker compose up --build` starts successfully from a clean state.
- App is reachable at `http://localhost:8000`.
- Seeded admin, agent, and customer logins work.
- Role redirects land on the correct pages.
- Customer cannot access admin or agent URLs.
- Agent cannot view unassigned complaints.
- Admin can view dashboard metrics.
- Chatbot returns account facts for seeded customer questions.

Optional automated tests:

- Role helper tests.
- Profile creation tests.
- Permission tests for major views.

## README Requirements

The root `README.md` should include:

- Project overview.
- Prerequisites.
- Environment setup.
- Docker run instructions.
- Automatic migration and seed explanation.
- Default seeded login credentials.
- Chatbot setup and `GROQ_API_KEY` requirement.
- Assumptions and design decisions.
- Troubleshooting notes for Docker and Groq.
