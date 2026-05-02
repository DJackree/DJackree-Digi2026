"""Complaint HTTP handlers (roles, workflows, and Bootstrap UI)."""

from __future__ import annotations

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from accounts.decorators import role_required
from accounts.models import UserProfile
from complaints.forms import (
    AdminStatusOverrideForm,
    ComplaintAssignmentForm,
    ComplaintCreateForm,
    ComplaintNoteForm,
    ComplaintStatusUpdateForm,
    EscalationForm,
)
from complaints.models import Complaint, ComplaintStatusHistory
from complaints.services import (
    add_complaint_note,
    assign_complaint,
    change_complaint_status,
    escalate_complaint,
    get_admin_complaints,
    get_agent_complaints,
    get_allowed_statuses,
    get_customer_complaints,
)
from customers.services import get_customer_account_for_user


def _sla_cutoff():
    return timezone.now() - timedelta(days=5)


def _complaint_age_days(complaint: Complaint) -> float:
    return (timezone.now() - complaint.created_at).total_seconds() / 86400


def _customer_timeline_rows(complaint: Complaint) -> list[dict[str, object]]:
    """Human-readable timeline for customers (no internal audit notes)."""

    labels = dict(Complaint.Status.choices)
    rows: list[dict[str, object]] = []
    for row in complaint.status_history.order_by("created_at"):
        from_label = labels.get(row.from_status, row.from_status or "—")
        to_label = labels.get(row.to_status, row.to_status)
        rows.append(
            {
                "from_label": from_label,
                "to_label": to_label,
                "at": row.created_at,
            }
        )
    return rows


@role_required(UserProfile.Role.CUSTOMER)
@require_http_methods(["GET", "HEAD"])
def customer_complaint_list(request):
    qs = get_customer_complaints(request.user).order_by("-created_at")
    return render(
        request,
        "complaints/customer_list.html",
        {"complaints": qs},
    )


@role_required(UserProfile.Role.CUSTOMER)
@require_http_methods(["GET", "HEAD", "POST"])
def customer_complaint_create(request):
    account = get_customer_account_for_user(request.user)
    if account is None:
        messages.error(request, "No customer account is linked to your user.")
        return redirect(reverse("accounts:customer_home"))

    if request.method == "POST":
        form = ComplaintCreateForm(request.POST)
        if form.is_valid():
            complaint = Complaint.objects.create(
                customer_account=account,
                category=form.cleaned_data["category"],
                description=form.cleaned_data["description"],
                status=Complaint.Status.OPEN,
            )
            ComplaintStatusHistory.objects.create(
                complaint=complaint,
                changed_by=request.user,
                from_status="",
                to_status=Complaint.Status.OPEN,
                note="Submitted by customer.",
            )
            messages.success(
                request,
                f"Complaint submitted as {complaint.reference}.",
            )
            return redirect(
                reverse(
                    "complaints:customer_complaint_detail",
                    kwargs={"reference": complaint.reference},
                )
            )
    else:
        form = ComplaintCreateForm()

    return render(
        request,
        "complaints/customer_form.html",
        {"form": form},
    )


@role_required(UserProfile.Role.CUSTOMER)
@require_http_methods(["GET", "HEAD"])
def customer_complaint_detail(request, reference: str):
    complaint = get_object_or_404(
        get_customer_complaints(request.user),
        reference=reference,
    )
    timeline_rows = _customer_timeline_rows(complaint)
    return render(
        request,
        "complaints/customer_detail.html",
        {
            "complaint": complaint,
            "timeline_rows": timeline_rows,
        },
    )


@role_required(UserProfile.Role.AGENT)
@require_http_methods(["GET", "HEAD"])
def agent_complaint_queue(request):
    valid_status = {s for s, _ in Complaint.Status.choices}
    valid_category = {c for c, _ in Complaint.Category.choices}

    qs = get_agent_complaints(request.user).order_by("created_at")
    filter_status = request.GET.get("status", "").strip()
    filter_category = request.GET.get("category", "").strip()

    if filter_status in valid_status:
        qs = qs.filter(status=filter_status)
    if filter_category in valid_category:
        qs = qs.filter(category=filter_category)

    cutoff = _sla_cutoff()
    rows = []
    for c in qs:
        rows.append(
            {
                "complaint": c,
                "age_days": _complaint_age_days(c),
                "sla_warning": c.created_at < cutoff
                and c.status
                not in (Complaint.Status.RESOLVED, Complaint.Status.CLOSED),
            }
        )
    return render(
        request,
        "complaints/agent_queue.html",
        {
            "rows": rows,
            "filter_status": filter_status,
            "filter_category": filter_category,
            "status_choices": Complaint.Status.choices,
            "category_choices": Complaint.Category.choices,
            "sla_cutoff": cutoff,
        },
    )


def _agent_complaint_or_404(request, reference: str) -> Complaint:
    return get_object_or_404(
        get_agent_complaints(request.user),
        reference=reference,
    )


@role_required(UserProfile.Role.AGENT)
@require_http_methods(["GET", "HEAD"])
def agent_complaint_detail(request, reference: str):
    complaint = _agent_complaint_or_404(request, reference)
    allowed = get_allowed_statuses(request.user, complaint)
    status_form = ComplaintStatusUpdateForm(allowed_statuses=allowed)
    note_form = ComplaintNoteForm()
    escalate_form = EscalationForm()
    can_escalate = complaint.status == Complaint.Status.IN_PROGRESS
    can_change_status = bool(allowed)
    notes = complaint.notes.order_by("-created_at")
    history = complaint.status_history.order_by("-created_at")
    return render(
        request,
        "complaints/agent_detail.html",
        {
            "complaint": complaint,
            "status_form": status_form,
            "note_form": note_form,
            "escalate_form": escalate_form,
            "can_escalate": can_escalate,
            "can_change_status": can_change_status,
            "notes": notes,
            "history": history,
            "sla_cutoff": _sla_cutoff(),
        },
    )


@role_required(UserProfile.Role.AGENT)
@require_POST
def agent_update_status(request, reference: str):
    complaint = _agent_complaint_or_404(request, reference)
    allowed = get_allowed_statuses(request.user, complaint)
    form = ComplaintStatusUpdateForm(
        request.POST,
        allowed_statuses=allowed,
    )
    if not form.is_valid():
        messages.error(request, "Could not update status (invalid input).")
        return redirect(
            reverse("complaints:agent_complaint_detail", kwargs={"reference": reference})
        )

    try:
        change_complaint_status(
            complaint=complaint,
            new_status=form.cleaned_data["status"],
            changed_by=request.user,
            note=form.cleaned_data.get("note") or "",
        )
        messages.success(request, "Status updated.")
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    except PermissionDenied as exc:
        messages.error(request, str(exc))

    return redirect(
        reverse("complaints:agent_complaint_detail", kwargs={"reference": reference})
    )


@role_required(UserProfile.Role.AGENT)
@require_POST
def agent_add_note(request, reference: str):
    complaint = _agent_complaint_or_404(request, reference)
    form = ComplaintNoteForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Could not add note (invalid input).")
        return redirect(
            reverse("complaints:agent_complaint_detail", kwargs={"reference": reference})
        )

    try:
        add_complaint_note(
            complaint=complaint,
            author=request.user,
            body=form.cleaned_data["body"],
            is_internal=True,
        )
        messages.success(request, "Note added.")
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    except PermissionDenied as exc:
        messages.error(request, str(exc))

    return redirect(
        reverse("complaints:agent_complaint_detail", kwargs={"reference": reference})
    )


@role_required(UserProfile.Role.AGENT)
@require_POST
def agent_escalate(request, reference: str):
    complaint = _agent_complaint_or_404(request, reference)
    form = EscalationForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Could not escalate (invalid input).")
        return redirect(
            reverse("complaints:agent_complaint_detail", kwargs={"reference": reference})
        )

    try:
        escalate_complaint(
            complaint=complaint,
            agent=request.user,
            reason=form.cleaned_data["reason"],
        )
        messages.success(request, "Complaint escalated.")
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    except PermissionDenied as exc:
        messages.error(request, str(exc))

    return redirect(
        reverse("complaints:agent_complaint_detail", kwargs={"reference": reference})
    )


def _admin_complaint_or_404(reference: str) -> Complaint:
    return get_object_or_404(get_admin_complaints(), reference=reference)


@role_required(UserProfile.Role.ADMIN)
@require_http_methods(["GET", "HEAD"])
def admin_complaint_list(request):
    valid_status = {s for s, _ in Complaint.Status.choices}
    valid_category = {c for c, _ in Complaint.Category.choices}

    qs = get_admin_complaints().order_by("-created_at")

    filter_status = request.GET.get("status", "").strip()
    filter_category = request.GET.get("category", "").strip()
    filter_agent = request.GET.get("agent", "").strip()
    filter_sla = request.GET.get("sla_breach", "").strip()

    if filter_status in valid_status:
        qs = qs.filter(status=filter_status)
    if filter_category in valid_category:
        qs = qs.filter(category=filter_category)

    if filter_agent:
        if filter_agent == "none":
            qs = qs.filter(assigned_agent__isnull=True)
        else:
            try:
                aid = int(filter_agent)
            except ValueError:
                aid = None
            if aid is not None:
                qs = qs.filter(assigned_agent_id=aid)

    cutoff = _sla_cutoff()
    if filter_sla == "1":
        qs = qs.exclude(
            status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED],
        ).filter(created_at__lt=cutoff)

    agents = User.objects.filter(profile__role=UserProfile.Role.AGENT).order_by("username")

    return render(
        request,
        "complaints/admin_list.html",
        {
            "complaints": qs,
            "agents": agents,
            "filter_status": filter_status,
            "filter_category": filter_category,
            "filter_agent": filter_agent,
            "filter_sla": filter_sla,
            "status_choices": Complaint.Status.choices,
            "category_choices": Complaint.Category.choices,
            "sla_cutoff": cutoff,
        },
    )


@role_required(UserProfile.Role.ADMIN)
@require_http_methods(["GET", "HEAD"])
def admin_complaint_detail(request, reference: str):
    complaint = _admin_complaint_or_404(reference)
    assign_form = ComplaintAssignmentForm()
    admin_status_form = AdminStatusOverrideForm()
    notes = complaint.notes.order_by("-created_at")
    history = complaint.status_history.order_by("-created_at")
    return render(
        request,
        "complaints/admin_detail.html",
        {
            "complaint": complaint,
            "assign_form": assign_form,
            "admin_status_form": admin_status_form,
            "notes": notes,
            "history": history,
        },
    )


@role_required(UserProfile.Role.ADMIN)
@require_POST
def admin_assign_complaint(request, reference: str):
    complaint = _admin_complaint_or_404(reference)
    form = ComplaintAssignmentForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Could not assign complaint (invalid input).")
        return redirect(
            reverse("complaints:admin_complaint_detail", kwargs={"reference": reference})
        )

    try:
        assign_complaint(
            complaint=complaint,
            agent=form.cleaned_data["agent"],
            assigned_by=request.user,
        )
        messages.success(request, "Agent assignment updated.")
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    except PermissionDenied as exc:
        messages.error(request, str(exc))

    return redirect(
        reverse("complaints:admin_complaint_detail", kwargs={"reference": reference})
    )


@role_required(UserProfile.Role.ADMIN)
@require_POST
def admin_update_status(request, reference: str):
    complaint = _admin_complaint_or_404(reference)
    form = AdminStatusOverrideForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Could not update status (invalid input).")
        return redirect(
            reverse("complaints:admin_complaint_detail", kwargs={"reference": reference})
        )

    try:
        change_complaint_status(
            complaint=complaint,
            new_status=form.cleaned_data["status"],
            changed_by=request.user,
            note=form.cleaned_data.get("note") or "",
        )
        messages.success(request, "Status updated (admin override).")
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    except PermissionDenied as exc:
        messages.error(request, str(exc))

    return redirect(
        reverse("complaints:admin_complaint_detail", kwargs={"reference": reference})
    )
