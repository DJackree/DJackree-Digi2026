# System Architecture Implementation Plan

## Purpose

This plan implements the project foundation that every later module depends on: Django project setup, PostgreSQL, Docker Compose, environment configuration, automatic startup flow, authentication, user roles, `UserProfile`, shared customer account data, base templates, and role-specific landing pages.

Build this plan before the complaint/fault module and chatbot module.

## Scope

This plan covers:

- Django project and app creation.
- PostgreSQL database setup.
- Docker and Docker Compose.
- Environment variables and `.env.example`.
- Entrypoint/startup flow.
- Automatic migrations.
- Automatic first-run seed command hook.
- Authentication.
- Customer, Agent, and Admin roles.
- `UserProfile`.
- Shared customer account models needed by later modules.
- Role helper functions/decorators.
- Base Bootstrap layout.
- Role-based landing redirects.
- Initial admin registration.
- README foundation instructions.

This plan does not implement complaint workflow or chatbot behavior. It creates the foundation those modules will build on.

## Target Project Structure

```text
requirements.txt
Dockerfile
docker-compose.yml
entrypoint.sh
.env.example
manage.py
config/
  settings.py
  urls.py
accounts/
  models.py
  decorators.py
  views.py
  urls.py
  admin.py
customers/
  models.py
  admin.py
core/
  management/commands/seed_data.py
templates/
  base.html
  accounts/login.html
  accounts/landing_customer.html
  accounts/landing_agent.html
  accounts/landing_admin.html
static/
```

`complaints`, `network`, `dashboard`, and `chatbot` apps can be created as placeholders here or during their module plans.

## Phase 1 - Database Setup

### Purpose

Configure PostgreSQL and create the foundation data model for users, roles, and customer account data used by complaints and chatbot responses.

### Files To Create Or Update

```text
docker-compose.yml
.env.example
config/settings.py
accounts/models.py
accounts/admin.py
customers/models.py
customers/admin.py
core/management/commands/seed_data.py
```

### Required Apps

- `accounts`: role profile and auth support.
- `customers`: service plans, account records, usage, and payments.
- `core`: optional cross-app management commands.

Register in `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # Django apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Local apps
    "accounts",
    "customers",
    "core",
]
```

### PostgreSQL Configuration

Use environment variables in `config/settings.py`:

```text
POSTGRES_DB=telecom_portal
POSTGRES_USER=telecom_user
POSTGRES_PASSWORD=
POSTGRES_HOST=db
POSTGRES_PORT=5432
```

Recommended database setting:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}
```

### Docker Database Service

`docker-compose.yml` should define:

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

### Environment Variables

`.env.example` should include:

```text
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
POSTGRES_DB=telecom_portal
POSTGRES_USER=telecom_user
POSTGRES_PASSWORD=change-me
POSTGRES_HOST=db
POSTGRES_PORT=5432
GROQ_API_KEY=
```

`GROQ_API_KEY` is included here so the final project has one env file, but it is only used by the chatbot plan.

### Models

#### `accounts.UserProfile`

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

- `user`: connects profile data to Django auth.
- `role`: drives access control and landing pages.
- `region`: supports later outage lookup and customer context.
- timestamps: helpful for admin inspection.

Constraints and indexes:

- One profile per user through `OneToOneField`.
- Index `role` because role filtering is common.

#### `customers.ServicePlan`

```python
class ServicePlan(models.Model):
    name = models.CharField(max_length=100, unique=True)
    monthly_price = models.DecimalField(max_digits=8, decimal_places=2)
    data_allowance_gb = models.DecimalField(max_digits=8, decimal_places=2)
    call_minutes = models.PositiveIntegerField()
    sms_allowance = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
```

Field rationale:

- Stores the customer plan facts required by account pages and chatbot answers.
- `name` is unique because seeded plans are stable demo records.

#### `customers.CustomerAccount`

```python
class CustomerAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="customer_account")
    account_number = models.CharField(max_length=30, unique=True, db_index=True)
    service_plan = models.ForeignKey(ServicePlan, on_delete=models.PROTECT, related_name="accounts")
    current_balance = models.DecimalField(max_digits=10, decimal_places=2)
    region = models.CharField(max_length=100, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

Field rationale:

- `user`: one account per seeded customer.
- `account_number`: customer-facing reference.
- `service_plan`: supports account display and chatbot plan lookup.
- `current_balance`: supports account display and chatbot balance lookup.
- `region`: supports outage matching.

Constraints and indexes:

- One account per user.
- Unique indexed account number.
- Index region for outage lookups.

#### `customers.AccountUsage`

```python
class AccountUsage(models.Model):
    account = models.ForeignKey(CustomerAccount, on_delete=models.CASCADE, related_name="usage_records")
    period_start = models.DateField()
    period_end = models.DateField()
    data_used_gb = models.DecimalField(max_digits=8, decimal_places=2)
    minutes_used = models.PositiveIntegerField(default=0)
    sms_used = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
```

Field rationale:

- Stores monthly aggregate usage for account pages and chatbot.
- Period fields let the app select the current usage window.

Indexes:

- Add index on `account, period_start, period_end`.

#### `customers.Payment`

```python
class Payment(models.Model):
    account = models.ForeignKey(CustomerAccount, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_at = models.DateTimeField(db_index=True)
    reference = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

Field rationale:

- Supports last payment display and chatbot lookup.
- `reference` is a stable payment identifier.

Indexes:

- Index `paid_at` for latest-payment queries.

### Migrations

Implementation tasks:

- Create initial migrations for `accounts` and `customers`.
- Run `python manage.py makemigrations`.
- Run `python manage.py migrate`.
- Confirm migrations run automatically through the entrypoint.

### Seed Data Hook

Create the command now even if module-specific seed content is expanded later:

```bash
python manage.py seed_data --if-empty
```

Foundation seed should create:

- 1 admin user.
- 3 agent users.
- 5 customer users.
- Matching `UserProfile` records.
- 3 service plans.
- 5 customer accounts.
- Usage and payment records.

Complaint and outage seed data are added in `02-complaint-and-fault-management-plan.md`.

### Acceptance Criteria

- PostgreSQL container starts successfully.
- Django connects to PostgreSQL using `.env`.
- `UserProfile`, `ServicePlan`, `CustomerAccount`, `AccountUsage`, and `Payment` migrations apply.
- Seed command creates foundation users and account records only when database is empty.
- Admin can inspect foundation models in Django admin.

### Risks Or Notes

- Avoid a custom user model unless the project starts with it; a profile model is simpler for this timebox.
- Keep seed passwords deterministic for assessment only.
- Do not commit `.env`.

## Phase 2 - API/Backend Setup

### Purpose

Create the Django backend foundation: project settings, app registration, auth routes, role redirects, authorization helpers, Docker web service, entrypoint flow, and initial error handling.

### Files To Create Or Update

```text
requirements.txt
Dockerfile
docker-compose.yml
entrypoint.sh
config/settings.py
config/urls.py
accounts/decorators.py
accounts/views.py
accounts/urls.py
customers/services.py
```

### Django Project Creation

Implementation tasks:

- Create project with `django-admin startproject config .`.
- Create apps with `python manage.py startapp accounts`, `customers`, and `core`.
- Add local apps to `INSTALLED_APPS`.
- Configure templates directory:

```python
TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"]
```

- Configure static files:

```python
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
```

### Dependencies

`requirements.txt` should include:

```text
Django
psycopg[binary]
groq
```

Use either direct `os.environ` or a small environment package. Keep configuration simple.

### Docker Web Service

`docker-compose.yml` should include:

```yaml
services:
  web:
    build: .
    command: ./entrypoint.sh
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db
```

`Dockerfile` should:

- Use a Python 3 base image.
- Set `/app` as working directory.
- Install requirements.
- Copy project files.
- Ensure `entrypoint.sh` is executable.

### Entrypoint Flow

`entrypoint.sh` should:

1. Wait until PostgreSQL accepts connections.
2. Run migrations.
3. Run seed command with `--if-empty`.
4. Start Django on port 8000.

```bash
python manage.py migrate --noinput
python manage.py seed_data --if-empty
python manage.py runserver 0.0.0.0:8000
```

### URL Routing

Foundation routes:

| Method | URL | Purpose | Access |
|---|---|---|---|
| GET | `/` | Role-aware landing redirect | Authenticated |
| GET/POST | `/accounts/login/` | Login | Anonymous |
| POST | `/accounts/logout/` | Logout | Authenticated |
| GET | `/customer/` | Customer landing placeholder | Customer |
| GET | `/agent/` | Agent landing placeholder | Agent |
| GET | `/admin-portal/` | Admin landing placeholder | Admin |

### Auth Views

Use Django's auth primitives:

- `LoginView` with custom template.
- `LogoutView`.
- `LoginRequiredMixin` or decorators for protected pages.

After login:

```python
def role_redirect(user):
    if user.profile.role == UserProfile.Role.CUSTOMER:
        return "customer_home"
    if user.profile.role == UserProfile.Role.AGENT:
        return "agent_home"
    if user.profile.role == UserProfile.Role.ADMIN:
        return "admin_home"
```

### Role Helpers And Decorators

Recommended `accounts/decorators.py`:

```python
def is_customer(user):
    return user.is_authenticated and user.profile.role == UserProfile.Role.CUSTOMER

def is_agent(user):
    return user.is_authenticated and user.profile.role == UserProfile.Role.AGENT

def is_admin(user):
    return user.is_authenticated and user.profile.role == UserProfile.Role.ADMIN

def role_required(*roles):
    ...
```

Authorization behavior:

- Anonymous users redirect to login.
- Authenticated users without the required role receive 403.
- Object-level access is enforced in later module querysets.

### Initial Admin Registration

Register:

- `UserProfile`
- `ServicePlan`
- `CustomerAccount`
- `AccountUsage`
- `Payment`

Use list displays and search fields for reviewer inspection.

### Error Handling

Foundation behavior:

- Return 403 for authenticated users with wrong role.
- Return 404 in later modules when an object is outside the user's scoped queryset.
- Show form errors inline for login failures.
- Use Django messages for successful login redirects and future actions.

### Acceptance Criteria

- `docker compose up --build` starts `web` and `db`.
- Entrypoint waits for database and runs migrations.
- Seed command runs automatically.
- Login/logout works.
- `/` redirects users by role.
- Role decorators block wrong-role access.
- Admin site is reachable for seeded admin.

### Risks Or Notes

- If `entrypoint.sh` is not executable on Windows checkout, document the fix or invoke it through `sh entrypoint.sh`.
- Keep auth helpers small and reusable; later modules depend on them.

## Phase 3 - UI Setup

### Purpose

Create the shared Bootstrap UI foundation, login page, role-specific landing pages, navigation, messages, and template structure.

### Files To Create Or Update

```text
templates/base.html
templates/accounts/login.html
templates/accounts/landing_customer.html
templates/accounts/landing_agent.html
templates/accounts/landing_admin.html
accounts/views.py
accounts/urls.py
README.md
```

### Base Bootstrap Layout

`templates/base.html` should include:

- Bootstrap CSS via CDN.
- Page title block.
- Top navigation.
- Role-aware links.
- Authenticated user and role display.
- Logout form/button.
- Flash message area.
- Main content block.
- Optional Bootstrap JS via CDN.

Navigation placeholders:

- Customer: Account, Complaints, Chatbot.
- Agent: Assigned Complaints.
- Admin: Dashboard, Complaints, Django Admin.

Links for complaints and chatbot can point to placeholders until plans `02` and `03` are implemented.

### Login Page

`templates/accounts/login.html` should:

- Extend `base.html`.
- Render username and password fields.
- Show validation errors.
- Submit to Django login view.
- Keep styling simple and readable.

### Logout Behavior

Use POST logout for safety:

- Show logout as a small form in the nav.
- Redirect to login after logout.

### Role-Specific Landing Pages

Customer landing:

- Account summary placeholder.
- Links to complaint history, new complaint, chatbot.

Agent landing:

- Link to assigned queue.
- Placeholder summary for assigned complaints.

Admin landing:

- Link to dashboard.
- Link to all complaints.
- Link to Django admin.

### Templates Directory Structure

```text
templates/
  base.html
  accounts/
    login.html
    landing_customer.html
    landing_agent.html
    landing_admin.html
```

Later modules add:

```text
templates/complaints/
templates/dashboard/
templates/chatbot/
```

### README Foundation Instructions

Add foundation run instructions:

```bash
cp .env.example .env
docker compose up --build
```

Document:

- Required env vars.
- URL: `http://localhost:8000`.
- Default seeded credentials.
- Migrations and seed command run automatically.

### UI Acceptance Criteria

- Login page renders with Bootstrap.
- Failed login shows an error.
- Successful login redirects by role.
- Navbar shows only links relevant to current role.
- Logout works.
- Flash messages render consistently.
- Customer, agent, and admin landing pages render without module-specific implementations.

### Manual Verification Steps

1. Start with `docker compose up --build`.
2. Log in as `admin`.
3. Confirm admin landing and Django admin access.
4. Log out.
5. Log in as `agent1`.
6. Confirm agent landing and admin links are not shown.
7. Log out.
8. Log in as `customer1`.
9. Confirm customer landing and chatbot/complaint placeholder links.
10. Attempt a wrong-role URL and confirm 403.

### Risks Or Notes

- Do not over-polish foundation UI. The main UI value will come from complaint, dashboard, and chatbot pages.
- Keep role-based link visibility aligned with backend permissions, but do not treat hidden links as security.
