from __future__ import annotations

from customers.models import CustomerAccount


def get_customer_account_for_user(user) -> CustomerAccount | None:
    """Return the CustomerAccount linked to ``user``, or ``None``.

    Agents and admins typically have no CustomerAccount row.
    """

    if not getattr(user, "is_authenticated", False):
        return None
    return getattr(user, "customer_account", None)
