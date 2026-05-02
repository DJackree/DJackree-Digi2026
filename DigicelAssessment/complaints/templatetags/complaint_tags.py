"""Template filters for complaint UI labels and badges."""

from django import template

from complaints.models import Complaint

register = template.Library()

_STATUS_LABELS = dict(Complaint.Status.choices)
_CATEGORY_LABELS = dict(Complaint.Category.choices)

_BADGE_MAP = {
    Complaint.Status.OPEN: "primary",
    Complaint.Status.IN_PROGRESS: "info",
    Complaint.Status.ESCALATED: "warning",
    Complaint.Status.RESOLVED: "success",
    Complaint.Status.CLOSED: "secondary",
}


@register.filter
def complaint_status_label(code: str) -> str:
    if not code:
        return ""
    return _STATUS_LABELS.get(code, code)


@register.filter
def complaint_category_label(code: str) -> str:
    if not code:
        return ""
    return _CATEGORY_LABELS.get(code, code)


@register.simple_tag
def complaint_status_badge_class(code: str) -> str:
    return _BADGE_MAP.get(code, "secondary")


@register.simple_tag
def complaint_category_badge_class(code: str) -> str:
    """Solid badge colors per category."""
    mapping = {
        Complaint.Category.BILLING: "secondary",
        Complaint.Category.NETWORK: "primary",
        Complaint.Category.DEVICE: "info",
        Complaint.Category.ROAMING: "success",
        Complaint.Category.OTHER: "dark",
    }
    return mapping.get(code, "secondary")
