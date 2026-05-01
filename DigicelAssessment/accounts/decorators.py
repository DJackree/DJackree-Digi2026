"""Role checks and decorators for Telecom Customer Portal."""

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
    """Return profile role string if present, otherwise None."""

    profile = getattr(user, "profile", None)
    if profile is None:
        return None
    return profile.role


def is_customer(user: object) -> bool:
    return bool(
        getattr(user, "is_authenticated", False)
        and user_profile_role(user) == UserProfile.Role.CUSTOMER,
    )


def is_agent(user: object) -> bool:
    return bool(
        getattr(user, "is_authenticated", False)
        and user_profile_role(user) == UserProfile.Role.AGENT,
    )


def is_admin(user: object) -> bool:
    return bool(
        getattr(user, "is_authenticated", False)
        and user_profile_role(user) == UserProfile.Role.ADMIN,
    )


def role_required(*roles: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    # Roles passed in by the caller, e.g. role_required(UserProfile.Role.CUSTOMER).
    # frozenset makes membership checks fast and the set immutable.
    allowed: frozenset[str] = frozenset(roles)

    # Outer factory: receives the real view function Django would call (customer_home, etc.).
    def decorator(view_func: Callable[P, R]) -> Callable[P, R]:
        # Preserve the wrapped view's name/docstring so debugging/tools stay readable.
        @wraps(view_func)
        def _wrapped(request: HttpRequest, *args: P.args, **kwargs: P.kwargs) -> HttpResponse | R:
            # Not logged in: send them to login and remember where they wanted to go (?next=...).
            if not request.user.is_authenticated:
                login_url_final = reverse(LOGIN_ROUTE)
                return redirect_to_login(
                    next=request.get_full_path(),
                    login_url=login_url_final,
                )

            # Logged in but missing UserProfile row: cannot decide role → hard stop (403).
            role_val = user_profile_role(request.user)
            if role_val is None:
                return HttpResponseForbidden("User profile is missing.")
            # Wrong role for this URL (agent hitting /customer/, etc.) → 403.
            if role_val not in allowed:
                return HttpResponseForbidden(
                    "You do not have permission to access this page."
                )

            # Passed all checks: run the actual view.
            return view_func(request, *args, **kwargs)

        return _wrapped

    # Calling role_required(...) returns the decorator that then wraps the view.
    return decorator
