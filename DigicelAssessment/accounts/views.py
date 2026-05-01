"""
Views for signing users in/out and sending each role to the right landing page.

URLs wire here from accounts/urls.py; permission checks on role-only pages use
accounts/decorators.role_required.
"""

from django.conf import settings
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme

from accounts.decorators import role_required
from accounts.forms import BootstrapAuthenticationForm
from accounts.models import UserProfile
from customers.services import get_customer_account_for_user


# Reverse name for the login page (used instead of hardcoding "/accounts/login/").
LOGIN_ROUTE_NAME = "accounts:login"


def _allowed_hosts(request) -> set[str]:
    """Hostnames we trust when validating a redirect target (?next=...) after login."""

    return {host for host in set(settings.ALLOWED_HOSTS) | {request.get_host()} if host}


class RoleAwareLoginView(LoginView):
    """Login view that respects safe ?next URLs, otherwise routes by profile role."""

    template_name = "accounts/login.html"
    authentication_form = BootstrapAuthenticationForm
    # If someone already logged in hits /accounts/login/, skip the form and redirect onward.
    redirect_authenticated_user = True

    def dispatch(self, request, *args, **kwargs):
        # Catch broken accounts: Django User exists but no UserProfile row (no role badge).
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and not hasattr(user, "profile"):
            return HttpResponseForbidden("User profile is missing.")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self) -> str:
        """Where to send the user after a successful login."""

        # Django's login flow stores "continue here after login" in `next` (GET or POST).
        redirect_field = self.redirect_field_name
        redirect_to = self.request.POST.get(
            redirect_field,
            self.request.GET.get(redirect_field, ""),
        ).strip()

        allowed_hosts_set = _allowed_hosts(self.request)

        # Only follow `next` if it stays on our site (blocks open-redirect tricks).
        if redirect_to:
            ok = url_has_allowed_host_and_scheme(
                redirect_to,
                allowed_hosts=allowed_hosts_set,
                require_https=self.request.is_secure(),
            )
            if ok:
                return redirect_to

        # No safe `next`: send them to the home URL that matches their role.
        return _post_login_fallback_url(self.request)


def role_home_redirect(request):
    """GET / redirects authenticated users to their role landing page."""

    # Visitors who are not signed in always start at login.
    if not request.user.is_authenticated:
        return redirect(reverse(LOGIN_ROUTE_NAME))

    # Signed-in user without a profile cannot pick a role destination.
    if not hasattr(request.user, "profile"):
        return HttpResponseForbidden("User profile is missing.")

    role_val = request.user.profile.role

    # Send each role to its own lobby page (URLs defined in accounts/urls.py).
    if role_val == UserProfile.Role.CUSTOMER:
        return redirect(reverse("accounts:customer_home"))
    if role_val == UserProfile.Role.AGENT:
        return redirect(reverse("accounts:agent_home"))
    if role_val == UserProfile.Role.ADMIN:
        return redirect(reverse("accounts:admin_home"))

    return HttpResponseForbidden("Unsupported user role.")


def _post_login_fallback_url(request) -> str:
    """Return the URL path to open after login when there is no usable ?next value."""

    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return reverse(LOGIN_ROUTE_NAME)

    if not hasattr(user, "profile"):
        return reverse(LOGIN_ROUTE_NAME)

    role_val = user.profile.role
    if role_val == UserProfile.Role.CUSTOMER:
        return reverse("accounts:customer_home")
    if role_val == UserProfile.Role.AGENT:
        return reverse("accounts:agent_home")
    if role_val == UserProfile.Role.ADMIN:
        return reverse("accounts:admin_home")
    return reverse(LOGIN_ROUTE_NAME)


class RoleLogoutView(LogoutView):
    """Logout via POST only (recommended); login page exposes a logout form."""

    # GET logout is easy to trigger accidentally or abuse; POST + CSRF is safer.
    http_method_names = ["post"]
    # After POST logout, send them back to the named login route.
    next_page = reverse_lazy("accounts:login")


@role_required(UserProfile.Role.CUSTOMER)
def customer_home(request):
    """Customer landing (Bootstrap Phase 3)."""

    account = get_customer_account_for_user(request.user)
    return render(
        request,
        "accounts/landing_customer.html",
        {"account": account},
    )


@role_required(UserProfile.Role.AGENT)
def agent_home(request):
    """Agent landing (Bootstrap Phase 3)."""

    return render(request, "accounts/landing_agent.html")


@role_required(UserProfile.Role.ADMIN)
def admin_home(request):
    """Admin landing (Bootstrap Phase 3)."""

    return render(request, "accounts/landing_admin.html")
