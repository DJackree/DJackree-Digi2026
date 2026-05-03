"""Tools that decide *who* may open a view (customer, agent, or admin).

Views use ``@role_required(...)`` so we do not repeat "if not logged in" and
"if wrong role" checks in every function. Helpers like ``is_customer`` are shared
with service-layer code (for example complaint permissions).
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.urls import reverse

from accounts.models import UserProfile

P = ParamSpec("P")
R = TypeVar("R")


LOGIN_ROUTE = "accounts:login"


def user_profile_role(user: object) -> str | None:
    """Return the role string from ``user.profile`` (for example ``"customer"``).

    If there is no profile (broken account), return ``None``.
    """
    profile = getattr(user, "profile", None)
    if profile is None:
        return None
    return profile.role


def is_customer(user: object) -> bool:
    """True when ``user`` is logged in and their profile role is customer."""
    return bool(
        getattr(user, "is_authenticated", False)
        and user_profile_role(user) == UserProfile.Role.CUSTOMER,
    )


def is_agent(user: object) -> bool:
    """True when ``user`` is logged in and their profile role is agent."""
    return bool(
        getattr(user, "is_authenticated", False)
        and user_profile_role(user) == UserProfile.Role.AGENT,
    )


def is_admin(user: object) -> bool:
    """True when ``user`` is logged in and their profile role is admin."""
    return bool(
        getattr(user, "is_authenticated", False)
        and user_profile_role(user) == UserProfile.Role.ADMIN,
    )


def role_required(*roles: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Wrap a view so only certain profile roles may open it.

    Behavior for each request:
    1. Not logged in → redirect to the login page (and remember ``?next=``).
    2. Logged in but no ``UserProfile`` → 403 (we cannot tell which menu they belong in).
    3. Logged in but role not in ``roles`` → 403 (for example agent opening a customer URL).
    4. Otherwise → run the real view.

    Example: ``@role_required(UserProfile.Role.CUSTOMER)`` on the chatbot page.
    """
    allowed: frozenset[str] = frozenset(roles)

    def decorator(view_func: Callable[P, R]) -> Callable[P, R]:
        @wraps(view_func)
        def _wrapped(request: HttpRequest, *args: P.args, **kwargs: P.kwargs) -> HttpResponse | R:
            if not request.user.is_authenticated:
                login_url_final = reverse(LOGIN_ROUTE)
                return redirect_to_login(
                    next=request.get_full_path(),
                    login_url=login_url_final,
                )

            role_val = user_profile_role(request.user)
            if role_val is None:
                return HttpResponseForbidden("User profile is missing.")
            if role_val not in allowed:
                return HttpResponseForbidden(
                    "You do not have permission to access this page."
                )

            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
