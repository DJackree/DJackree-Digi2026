"""Template tags for shared layout (Phase 3)."""

from django import template
from django.core.exceptions import ObjectDoesNotExist

register = template.Library()


@register.simple_tag
def safe_user_profile(user):
    """Return ``user.profile`` when it exists, else ``None`` (no exception)."""

    if not getattr(user, "is_authenticated", False):
        return None
    try:
        return user.profile
    except ObjectDoesNotExist:
        return None
