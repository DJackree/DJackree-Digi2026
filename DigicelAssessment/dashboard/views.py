"""Admin dashboard view (Phase 2 minimal UI)."""

from django.shortcuts import render

from accounts.decorators import role_required
from accounts.models import UserProfile

from .services import get_dashboard_metrics


@role_required(UserProfile.Role.ADMIN)
def admin_dashboard(request):
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

    return render(
        request,
        "dashboard/admin_dashboard.html",
        {
            "metrics": metrics,
            "average_resolution_display": avg_display,
        },
    )
