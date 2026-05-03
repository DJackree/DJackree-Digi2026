"""Small helpers for reading customer account data from a logged-in user.

Only users with role *customer* normally have a ``CustomerAccount`` row. Agents
and admins use the complaints tools without a linked account here.
"""

from __future__ import annotations

from customers.models import CustomerAccount


def get_customer_account_for_user(user) -> CustomerAccount | None:
    """Return the customer's ``CustomerAccount``, or ``None`` if there isn't one."""

    if not getattr(user, "is_authenticated", False):
        return None
    return getattr(user, "customer_account", None)
