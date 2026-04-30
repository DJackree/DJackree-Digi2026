# Complaint And Fault Management Implementation Plan

## Purpose

This plan implements the Complaint and Fault Management module after the project foundation in `01-system-architecture-plan.md` is complete. It covers customer complaint submission and tracking, agent work queues, admin complaint management, workflow enforcement, notes, escalation, status history, SLA logic, dashboard metrics, network outage/fault records, and module seed data.

## Dependencies From Plan 01

This plan assumes these foundation pieces already exist:

- Django project, PostgreSQL, Docker Compose, and entrypoint.
- `accounts.UserProfile` with Customer, Agent, and Admin roles.
- Role helpers/decorators.
- Login/logout and role redirects.
- Bootstrap base template.
- `customers.CustomerAccount`.
- Foundation seed users and customer account records.

## Module Scope

In scope:

- Customer complaint creation, history, and detail.
- Complaint categories: Billing, Network, Device, Roaming, Other.
- Complaint statuses: Open, In Progress, Escalated, Resolved, Closed.
- Agent assigned queue sorted by age.
- Agent status updates.
- Agent internal notes.
- Agent escalation with reason.
- Admin all-complaints view.
- Admin assignment/reassignment.
- Admin status override.
- Complaint status history.
- SLA threshold logic.
- Admin dashboard metrics.
- Network outage/fault records.
- Complaint and outage seed data.

Out of scope:

- Real telecom fault integrations.
- Email/SMS notifications.
- Production ticketing integrations.
- Complex reporting exports.

## Core Workflow Rules

Required lifecycle:

```text
Open -> In Progress -> Escalated -> Resolved -> Closed
```

Customer:

- Can create complaints for their own account.
- Can view only their own complaint history and detail.
- Cannot change status.
- Cannot see internal notes.

Agent:

- Can view only complaints assigned to them.
- Can add internal notes.
- Can move assigned complaints forward through the workflow.
- Can flag escalation with a reason.

Admin:

- Can view all complaints.
- Can assign and reassign complaints to agents.
- Can move complaints to any valid status.
- Can view dashboard metrics and SLA breaches.

SLA:

- Threshold is 5 days from `created_at`.
- A complaint breaches SLA when it is older than 5 days and not `Resolved` or `Closed`.
- Average resolution time uses `resolved_at - created_at`.

## Phase 1 - Database Setup

### Purpose

Create the complaint, note, status history, and outage/fault data model. Add indexes and seed records needed to exercise customer, agent, admin, dashboard, SLA, and chatbot outage flows.

### Files To Create Or Update

```text
complaints/models.py
complaints/admin.py
network/models.py
network/admin.py
dashboard/__init__.py
core/management/commands/seed_data.py
config/settings.py
```

If `network` and `dashboard` apps were not created in plan `01`, create them here:

```bash
python manage.py startapp complaints
python manage.py startapp network
python manage.py startapp dashboard
```

Register them in `INSTALLED_APPS`.

### `complaints.Complaint`

```python
class Complaint(models.Model):
    class Category(models.TextChoices):
        BILLING = "billing", "Billing"
        NETWORK = "network", "Network"
        DEVICE = "device", "Device"
        ROAMING = "roaming", "Roaming"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        ESCALATED = "escalated", "Escalated"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    reference = models.CharField(max_length=20, unique=True, db_index=True)
    customer_account = models.ForeignKey(
        "customers.CustomerAccount",
        on_delete=models.CASCADE,
        related_name="complaints",
    )
    category = models.CharField(max_length=30, choices=Category.choices, db_index=True)
    description = models.TextField()
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.OPEN, db_index=True)
    assigned_agent = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_complaints",
    )
    escalation_reason = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
```

Field rationale:

- `reference`: customer-facing tracking number such as `CMP-2026-0001`.
- `customer_account`: complaint ownership and customer scoping.
- `category`: supports filtering and dashboard grouping.
- `description`: customer-submitted issue details.
- `status`: current workflow state.
- `assigned_agent`: drives agent queue.
- `escalation_reason`: records why escalation occurred.
- `resolved_at`: supports average resolution calculation.
- timestamps: support sorting, SLA, and audit.

Constraints and indexes:

- Unique indexed `reference`.
- Index `status`, `category`, `assigned_agent`, `created_at`, and `resolved_at`.
- `assigned_agent` uses `SET_NULL` so records survive agent deletion.

### `complaints.ComplaintNote`

```python
class ComplaintNote(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name="complaint_notes")
    body = models.TextField()
    is_internal = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

Field rationale:

- Stores note history instead of overwriting one text field.
- `is_internal` prevents customer-facing leakage.
- `PROTECT` keeps note authors available for audit.

Indexes:

- Add index on `complaint, created_at`.

### `complaints.ComplaintStatusHistory`

```python
class ComplaintStatusHistory(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="status_history")
    changed_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="complaint_status_changes")
    from_status = models.CharField(max_length=30, blank=True)
    to_status = models.CharField(max_length=30)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

Field rationale:

- Records every workflow transition.
- Supports auditability during interview walkthrough.
- Allows customer-visible timeline if desired while still hiding internal notes.

Indexes:

- Add index on `complaint, created_at`.

### `network.NetworkOutage`

```python
class NetworkOutage(models.Model):
    region = models.CharField(max_length=100, db_index=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    started_at = models.DateTimeField()
    estimated_resolution_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

Field rationale:

- Supports outage/fault data tied to customer regions.
- Used by admin inspection and later chatbot active outage lookup.
- `is_active` keeps queries simple.

Indexes:

- Index `region`.
- Index `is_active`.

### Reference Generation

Create a helper or model method to generate unique references:

```text
CMP-2026-0001
CMP-2026-0002
```

Keep it deterministic and simple. A service function is preferred over complex database sequences for this assessment.

### Migrations

Implementation tasks:

- Add `complaints`, `network`, and `dashboard` apps.
- Run `makemigrations`.
- Run `migrate`.
- Confirm entrypoint applies migrations automatically on startup.

### Seed Data Needed For This Module

Extend `seed_data --if-empty` to create:

- 15 complaints distributed across all statuses.
- Complaints across Billing, Network, Device, Roaming, and Other categories.
- Mix of assigned and unassigned complaints.
- Complaints assigned across all 3 seeded agents.
- At least 2 unresolved complaints older than 5 days for SLA breach testing.
- Status history records matching seeded complaint statuses.
- Internal notes on several assigned complaints.
- At least 2 `NetworkOutage` records.
- At least 1 active outage matching a seeded customer region.

### Acceptance Criteria

- Complaint, note, status history, and outage migrations apply.
- Seed data includes required complaint and outage records.
- Admin site shows complaint and outage records.
- SLA breach test data exists.
- Seed data supports customer, agent, admin, dashboard, and chatbot outage scenarios.

### Risks Or Notes

- Do not store internal notes on the `Complaint` model as a single field; use `ComplaintNote`.
- Ensure customer-facing code never exposes `ComplaintNote` records where `is_internal=True`.
- Keep status/category as model choices unless requirements expand.

## Phase 2 - API/Backend Setup

### Purpose

Implement complaint routes, forms, services, permissions, workflow validation, SLA logic, and dashboard queries.

### Files To Create Or Update

```text
complaints/forms.py
complaints/services.py
complaints/views.py
complaints/urls.py
dashboard/services.py
dashboard/views.py
dashboard/urls.py
network/admin.py
config/urls.py
accounts/decorators.py
```

### URL Structure

Customer routes:

| Method | URL | Purpose | Access |
|---|---|---|---|
| GET | `/complaints/` | Own complaint history | Customer |
| GET | `/complaints/new/` | New complaint form | Customer |
| POST | `/complaints/new/` | Create complaint | Customer |
| GET | `/complaints/<reference>/` | Own complaint detail | Customer |

Agent routes:

| Method | URL | Purpose | Access |
|---|---|---|---|
| GET | `/agent/complaints/` | Assigned queue sorted by age | Agent |
| GET | `/agent/complaints/<reference>/` | Assigned complaint detail | Agent |
| POST | `/agent/complaints/<reference>/status/` | Move status forward | Agent |
| POST | `/agent/complaints/<reference>/notes/` | Add internal note | Agent |
| POST | `/agent/complaints/<reference>/escalate/` | Escalate with reason | Agent |

Admin routes:

| Method | URL | Purpose | Access |
|---|---|---|---|
| GET | `/admin-portal/dashboard/` | Complaint metrics dashboard | Admin |
| GET | `/admin-portal/complaints/` | All complaints | Admin |
| GET | `/admin-portal/complaints/<reference>/` | Complaint detail | Admin |
| POST | `/admin-portal/complaints/<reference>/assign/` | Assign/reassign agent | Admin |
| POST | `/admin-portal/complaints/<reference>/status/` | Override status | Admin |

### Forms

Create:

- `ComplaintCreateForm`: category and description.
- `ComplaintStatusUpdateForm`: target status and note.
- `ComplaintNoteForm`: note body.
- `EscalationForm`: reason.
- `ComplaintAssignmentForm`: agent selection.
- `AdminStatusOverrideForm`: target status and note.

Validation rules:

- Category is required.
- Description is required and should have a minimum practical length.
- Escalation reason is required.
- Assignment target must be a user with Agent role.
- Customer cannot submit for another customer account.
- Agent cannot update unassigned complaints.
- Agent cannot move backward.
- Admin can choose any valid status.

### Workflow Service

Create `complaints/services.py`:

```python
AGENT_FORWARD_TRANSITIONS = {
    "open": ["in_progress"],
    "in_progress": ["escalated", "resolved"],
    "escalated": ["resolved"],
    "resolved": ["closed"],
    "closed": [],
}

def get_allowed_statuses(user, complaint):
    ...

def change_complaint_status(*, complaint, new_status, changed_by, note=""):
    ...

def assign_complaint(*, complaint, agent, assigned_by):
    ...

def add_complaint_note(*, complaint, author, body, is_internal=True):
    ...
```

Service responsibilities:

- Enforce role permissions.
- Validate target status.
- Set `resolved_at` when first entering `Resolved`.
- Create `ComplaintStatusHistory`.
- Create optional status-change note.
- Save complaint updates atomically.

### SLA Service

Create dashboard or complaint service functions:

```python
def get_sla_breaches():
    return Complaint.objects.exclude(
        status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED]
    ).filter(
        created_at__lt=timezone.now() - timedelta(days=5)
    )
```

Average resolution:

```python
def get_average_resolution_time():
    resolved = Complaint.objects.filter(resolved_at__isnull=False)
    ...
```

### Dashboard Query Service

Create `dashboard/services.py`:

```python
def get_dashboard_metrics():
    return {
        "by_status": ...,
        "by_category": ...,
        "average_resolution_time": ...,
        "sla_breaches": ...,
    }
```

Required metrics:

- Total complaints by status.
- Total complaints by category.
- Average resolution time.
- SLA breach list.

### Permission Checks

Customer querysets:

```python
Complaint.objects.filter(customer_account__user=request.user)
```

Agent querysets:

```python
Complaint.objects.filter(assigned_agent=request.user)
```

Admin querysets:

```python
Complaint.objects.all()
```

Use:

- Role decorators for route access.
- Scoped querysets before object lookup.
- 404 for inaccessible objects inside a scoped queryset.
- 403 for wrong-role route access.

### Request/Response Examples

Customer complaint create fields:

```json
{
  "category": "network",
  "description": "Mobile data has been unavailable since this morning."
}
```

Agent status update fields:

```json
{
  "status": "in_progress",
  "note": "Customer contacted. Investigation started."
}
```

Agent escalation fields:

```json
{
  "reason": "Issue appears related to a wider regional network fault."
}
```

Admin assignment fields:

```json
{
  "agent_id": 12
}
```

### Error Handling

- Invalid form input: re-render page with inline errors.
- Wrong role: return 403.
- Object outside scoped queryset: return 404.
- Invalid workflow transition: show form error.
- Missing escalation reason: show form error.

### Acceptance Criteria

- Customer can create and view only their complaints.
- Customer cannot change status or see internal notes.
- Agent can view only assigned complaints.
- Agent can add internal notes.
- Agent can move assigned complaints through allowed workflow steps.
- Agent escalation requires reason.
- Admin can view all complaints.
- Admin can assign/reassign agents.
- Admin can set any valid status.
- Every status change creates history.
- SLA service returns seeded breaches.
- Dashboard service returns all required metrics.

### Risks Or Notes

- Avoid duplicating status logic in views. Keep workflow rules in `complaints/services.py`.
- Avoid filtering only in templates. Querysets must enforce ownership and assignment.
- Keep dashboard queries simple and explainable.

## Phase 3 - UI Setup

### Purpose

Create customer, agent, and admin complaint interfaces using Bootstrap templates. Include the admin dashboard and clear SLA breach display.

### Files To Create Or Update

```text
templates/complaints/customer_list.html
templates/complaints/customer_detail.html
templates/complaints/customer_form.html
templates/complaints/agent_queue.html
templates/complaints/agent_detail.html
templates/complaints/admin_list.html
templates/complaints/admin_detail.html
templates/dashboard/admin_dashboard.html
templates/base.html
complaints/views.py
dashboard/views.py
```

### Customer Pages

Complaint list:

- Table columns: reference, category, status, submitted date, last updated.
- Link each row to detail.
- Button to submit new complaint.
- Empty state when no complaints exist.

Complaint create:

- Category dropdown.
- Description textarea.
- Submit/cancel buttons.
- Inline validation errors.

Complaint detail:

- Reference, category, description, status, submitted date, last updated.
- Customer-visible status timeline.
- No internal notes.
- No status update controls.

### Agent Pages

Assigned queue:

- Complaints assigned to current agent only.
- Sort oldest first.
- Show reference, customer, category, status, age, SLA warning.
- Filter by status/category if time permits.

Agent detail:

- Customer/account summary.
- Complaint description.
- Current status.
- Internal notes list.
- Add note form.
- Status update form showing allowed next statuses only.
- Escalation form requiring reason.

### Admin Pages

All complaints:

- Table of all complaints.
- Filters for status, category, agent, and SLA breach if time permits.
- Links to complaint details.

Admin detail:

- Full complaint information.
- Assignment/reassignment form.
- Status override form with all statuses.
- Full notes and status history.
- Clear warning that admin overrides are audited.

### Admin Dashboard

Dashboard components:

- Cards for total complaints by status.
- Table for totals by category.
- Average resolution time card.
- SLA breach table with reference, customer, category, age, assigned agent, and link to detail.

Dashboard behavior:

- Breach list excludes resolved and closed complaints.
- Metric cards can link to filtered lists if time allows.

### Role-Based UI Differences

- Customer nav shows complaint history and submit complaint.
- Agent nav shows assigned queue.
- Admin nav shows dashboard and all complaints.
- Templates should hide unavailable actions, but backend permissions remain authoritative.

### Manual UI Acceptance Criteria

Customer:

- Can submit complaint.
- Sees success message after create.
- Sees complaint in history.
- Cannot see internal notes or status forms.

Agent:

- Sees assigned queue.
- Can add note.
- Can update status forward.
- Can escalate with reason.
- Cannot access another agent's complaint.

Admin:

- Sees dashboard metrics.
- Sees all complaints.
- Can assign complaint to agent.
- Can override status.
- Can view status history.

SLA:

- Dashboard shows seeded SLA breaches.
- Breach rows link to complaint detail.

### Manual Verification Steps

1. Log in as `customer1` and create a network complaint.
2. Confirm it starts as `Open`.
3. Confirm `customer2` cannot view `customer1` complaint.
4. Log in as `agent1` and open an assigned complaint.
5. Add an internal note.
6. Move status from `Open` to `In Progress`.
7. Escalate an eligible complaint with a reason.
8. Confirm status history records the changes.
9. Log in as `admin`.
10. Assign an unassigned complaint to `agent2`.
11. Override a complaint status.
12. Confirm dashboard counts and SLA breach list update.

### Risks Or Notes

- Keep templates functional before adding polish.
- Do not expose internal notes to customers through shared partials.
- Avoid building custom user management unless core flows are complete; Django admin is enough.
