"""Dashboard metrics derived from complaints."""

from __future__ import annotations

from complaints.models import Complaint
from complaints.services import get_average_resolution_time, get_sla_breaches


def get_dashboard_metrics():
    return {
        "by_status": {
            status: Complaint.objects.filter(status=status).count()
            for status, _ in Complaint.Status.choices
        },
        "by_category": {
            cat: Complaint.objects.filter(category=cat).count()
            for cat, _ in Complaint.Category.choices
        },
        "average_resolution_time": get_average_resolution_time(),
        "sla_breaches": get_sla_breaches(),
    }
