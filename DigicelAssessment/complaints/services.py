"""Business rules for complaints: who may do what, and how status changes work.

Views should call these functions instead of editing ``Complaint`` rows directly,
so workflow rules and audit notes stay consistent.
"""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from accounts.decorators import is_admin, is_agent
from accounts.models import UserProfile
from complaints.models import Complaint, ComplaintNote, ComplaintStatusHistory


AGENT_FORWARD_TRANSITIONS: dict[str, list[str]] = {
    Complaint.Status.OPEN: [Complaint.Status.IN_PROGRESS],
    Complaint.Status.IN_PROGRESS: [Complaint.Status.ESCALATED, Complaint.Status.RESOLVED],
    Complaint.Status.ESCALATED: [Complaint.Status.RESOLVED],
    Complaint.Status.RESOLVED: [Complaint.Status.CLOSED],
    Complaint.Status.CLOSED: [],
}


def get_customer_complaints(user: User) -> QuerySet[Complaint]:
    """Tickets that belong to this customer's linked account."""

    return Complaint.objects.filter(customer_account__user=user)


def get_agent_complaints(user: User) -> QuerySet[Complaint]:
    """Tickets currently assigned to this agent user."""

    return Complaint.objects.filter(assigned_agent=user)


def get_admin_complaints() -> QuerySet[Complaint]:
    """Every ticket in the system (admin reporting and assignment screens)."""

    return Complaint.objects.all()


def get_allowed_statuses(user: User, complaint: Complaint) -> list[str]:
    """Statuses this user may move the ticket to *from its current status*."""

    if is_admin(user):
        return [s for s, _ in Complaint.Status.choices]
    if is_agent(user):
        return AGENT_FORWARD_TRANSITIONS.get(complaint.status, [])
    return []


def _ensure_agent_assigned(user: User, complaint: Complaint) -> None:
    """Raise a validation error unless this agent owns the ticket."""

    if complaint.assigned_agent_id != user.id:
        raise ValidationError("You can only work on complaints assigned to you.")


def change_complaint_status(
    *,
    complaint: Complaint,
    new_status: str,
    changed_by: User,
    note: str = "",
) -> Complaint:
    """Move a ticket to a new status, writing history (and optional internal note).

    Enforces agent workflow steps; admins may jump to any valid status code.
    """

    valid = {s for s, _ in Complaint.Status.choices}
    if new_status not in valid:
        raise ValidationError("Invalid status.")

    if is_admin(changed_by):
        pass
    elif is_agent(changed_by):
        _ensure_agent_assigned(changed_by, complaint)
        allowed = AGENT_FORWARD_TRANSITIONS.get(complaint.status, [])
        if new_status not in allowed:
            raise ValidationError("That status change is not allowed.")
    else:
        raise PermissionDenied("Only agents and admins can change complaint status.")

    old_status = complaint.status
    if old_status == new_status:
        raise ValidationError("Complaint is already in that status.")

    note_clean = (note or "").strip()

    with transaction.atomic():
        complaint.status = new_status

        if new_status in (Complaint.Status.RESOLVED, Complaint.Status.CLOSED):
            if complaint.resolved_at is None:
                complaint.resolved_at = timezone.now()
        elif old_status in (Complaint.Status.RESOLVED, Complaint.Status.CLOSED):
            # Moving backward from "done" states clears the resolution timestamp unless still terminal.
            if is_admin(changed_by) and new_status not in (
                Complaint.Status.RESOLVED,
                Complaint.Status.CLOSED,
            ):
                complaint.resolved_at = None

        complaint.save()

        ComplaintStatusHistory.objects.create(
            complaint=complaint,
            changed_by=changed_by,
            from_status=old_status,
            to_status=new_status,
            note=note_clean,
        )

        if note_clean and (is_agent(changed_by) or is_admin(changed_by)):
            ComplaintNote.objects.create(
                complaint=complaint,
                author=changed_by,
                body=f"Status change note ({old_status} → {new_status}): {note_clean}",
                is_internal=True,
            )

    return complaint


def assign_complaint(*, complaint: Complaint, agent: User, assigned_by: User) -> Complaint:
    """Point a ticket at an agent and leave an internal note who did it."""

    if not is_admin(assigned_by):
        raise PermissionDenied("Only admins can assign complaints.")

    if not UserProfile.objects.filter(
        user=agent,
        role=UserProfile.Role.AGENT,
    ).exists():
        raise ValidationError("Assignment target must be an agent.")

    with transaction.atomic():
        prev = complaint.assigned_agent
        complaint.assigned_agent = agent
        complaint.save(
            update_fields=["assigned_agent", "updated_at"],
        )
        prev_name = getattr(prev, "username", None) or "unassigned"
        ComplaintNote.objects.create(
            complaint=complaint,
            author=assigned_by,
            body=f"Assignment: {prev_name} → {agent.username}",
            is_internal=True,
        )

    return complaint


def add_complaint_note(*, complaint: Complaint, author: User, body: str, is_internal: bool = True) -> ComplaintNote:
    """Attach a free-text note; agents may only note on their own assigned tickets."""

    if not (is_agent(author) or is_admin(author)):
        raise PermissionDenied("Only agents and admins can add notes.")

    if is_agent(author):
        _ensure_agent_assigned(author, complaint)

    body_clean = body.strip()
    if not body_clean:
        raise ValidationError("Note body is required.")

    return ComplaintNote.objects.create(
        complaint=complaint,
        author=author,
        body=body_clean,
        is_internal=is_internal,
    )


def escalate_complaint(*, complaint: Complaint, agent: User, reason: str) -> Complaint:
    """Agent-only path: store escalation text and force status to Escalated."""

    if not is_agent(agent):
        raise PermissionDenied("Only agents can escalate assigned complaints.")

    _ensure_agent_assigned(agent, complaint)

    reason_clean = reason.strip()
    if not reason_clean:
        raise ValidationError("Escalation reason is required.")

    with transaction.atomic():
        complaint.escalation_reason = reason_clean
        complaint.save(update_fields=["escalation_reason", "updated_at"])
        change_complaint_status(
            complaint=complaint,
            new_status=Complaint.Status.ESCALATED,
            changed_by=agent,
            note=f"Escalated: {reason_clean}",
        )

    complaint.refresh_from_db()
    return complaint


def get_sla_breaches() -> QuerySet[Complaint]:
    """Tickets still open after five days since submission (used on admin dashboard)."""

    cutoff = timezone.now() - timedelta(days=5)
    return Complaint.objects.exclude(
        status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED],
    ).filter(created_at__lt=cutoff)


def get_average_resolution_time():
    """Average time from ticket creation to resolution across all resolved tickets."""

    qs = Complaint.objects.filter(resolved_at__isnull=False).only("created_at", "resolved_at")
    deltas: list[timedelta] = []
    for row in qs.iterator():
        deltas.append(row.resolved_at - row.created_at)
    if not deltas:
        return None
    total_seconds = sum(d.total_seconds() for d in deltas) / len(deltas)
    return timedelta(seconds=total_seconds)
