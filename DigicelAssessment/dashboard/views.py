"""Admin-only summary page for complaint volume and SLA risk.

Uses ``get_dashboard_metrics`` so the math stays in one place for tests and reuse.
"""

from django.shortcuts import render
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import UserProfile
from complaints.models import Complaint

from .services import get_dashboard_metrics


def _complaint_age_days(complaint: Complaint) -> float:
    """Days since the ticket was opened (used beside SLA breach table rows)."""

    return (timezone.now() - complaint.created_at).total_seconds() / 86400


@role_required(UserProfile.Role.ADMIN)
def admin_dashboard(request):
    """Render cards and tables: counts by status/category, average resolution, SLA list."""

    metrics = get_dashboard_metrics()
    avg = metrics["average_resolution_time"]
    avg_display = None
    if avg is not None:
        total_seconds = int(avg.total_seconds())
        days, rem = divmod(total_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes or not parts:
            parts.append(f"{minutes}m")
        avg_display = " ".join(parts)

    status_cards = [
        {"code": code, "label": label, "count": metrics["by_status"][code]}
        for code, label in Complaint.Status.choices
    ]
    category_rows = [
        {"code": code, "label": label, "count": metrics["by_category"][code]}
        for code, label in Complaint.Category.choices
    ]

    breaches = list(metrics["sla_breaches"])
    sla_breach_rows = [
        {"complaint": c, "age_days": _complaint_age_days(c)} for c in breaches
    ]

    return render(
        request,
        "dashboard/admin_dashboard.html",
        {
            "metrics": metrics,
            "average_resolution_display": avg_display,
            "status_cards": status_cards,
            "category_rows": category_rows,
            "sla_breach_rows": sla_breach_rows,
        },
    )
