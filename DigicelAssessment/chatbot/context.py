"""Customer-scoped context builders for deterministic chat replies."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.utils import timezone

from complaints.models import Complaint
from customers.models import AccountUsage, CustomerAccount, Payment
from customers.services import get_customer_account_for_user
from network.models import NetworkOutage


OPEN_STATUSES = {
    Complaint.Status.OPEN,
    Complaint.Status.IN_PROGRESS,
    Complaint.Status.ESCALATED,
}


def _money_str(amount: Decimal) -> str:
    return f"{amount.quantize(Decimal('0.01'))}"


def build_plan_context(*, account: CustomerAccount | None) -> dict[str, Any]:
    if account is None:
        return {"intent": "current_plan", "plan": None}
    plan = account.service_plan
    return {
        "intent": "current_plan",
        "plan": {
            "name": plan.name,
            "monthly_price": _money_str(plan.monthly_price),
            "data_allowance_gb": _money_str(plan.data_allowance_gb),
            "call_minutes": plan.call_minutes,
            "sms_allowance": plan.sms_allowance,
        },
    }


def build_balance_context(*, account: CustomerAccount | None) -> dict[str, Any]:
    if account is None:
        return {"intent": "account_balance", "current_balance": None}
    return {
        "intent": "account_balance",
        "current_balance": _money_str(account.current_balance),
    }


def _current_usage_record(account: CustomerAccount) -> AccountUsage | None:
    today = timezone.now().date()
    scoped = (
        AccountUsage.objects.filter(account=account, period_start__lte=today, period_end__gte=today)
        .order_by("-period_end")
        .first()
    )
    if scoped:
        return scoped
    return AccountUsage.objects.filter(account=account).order_by("-period_end").first()


def build_usage_context(*, account: CustomerAccount | None) -> dict[str, Any]:
    if account is None:
        return {"intent": "data_usage", "usage": None, "plan": None}
    plan = account.service_plan
    usage = _current_usage_record(account)
    if usage is None:
        return {
            "intent": "data_usage",
            "usage": None,
            "plan": {"data_allowance_gb": _money_str(plan.data_allowance_gb)},
            "period": None,
        }
    return {
        "intent": "data_usage",
        "period": {"start": usage.period_start.isoformat(), "end": usage.period_end.isoformat()},
        "usage": {
            "data_used_gb": _money_str(usage.data_used_gb),
            "minutes_used": usage.minutes_used,
            "sms_used": usage.sms_used,
        },
        "plan": {"data_allowance_gb": _money_str(plan.data_allowance_gb)},
    }


def build_complaints_context(*, account: CustomerAccount | None) -> dict[str, Any]:
    if account is None:
        return {"intent": "open_complaints", "complaints": []}
    category_labels = dict(Complaint.Category.choices)
    status_labels = dict(Complaint.Status.choices)

    qs = (
        Complaint.objects.filter(customer_account=account, status__in=OPEN_STATUSES)
        .only("reference", "category", "status", "created_at")
        .order_by("-created_at")
    )
    rows = []
    for c in qs:
        rows.append(
            {
                "reference": c.reference,
                "category": category_labels.get(c.category, c.category),
                "status": status_labels.get(c.status, c.status),
                "submitted_at": timezone.localtime(c.created_at).date().isoformat(),
            }
        )
    return {"intent": "open_complaints", "complaints": rows}


def build_payment_context(*, account: CustomerAccount | None) -> dict[str, Any]:
    if account is None:
        return {"intent": "last_payment", "payment": None}
    p = Payment.objects.filter(account=account).order_by("-paid_at").only("amount", "paid_at", "reference").first()
    if p is None:
        return {"intent": "last_payment", "payment": None}
    return {
        "intent": "last_payment",
        "payment": {
            "amount": _money_str(p.amount),
            "paid_at": timezone.localtime(p.paid_at).isoformat(timespec="seconds"),
            "reference": p.reference,
        },
    }


def build_outage_context(*, account: CustomerAccount | None) -> dict[str, Any]:
    if account is None:
        return {"intent": "active_outages", "region": None, "outages": []}

    outages = []
    qs = NetworkOutage.objects.filter(is_active=True, region__iexact=account.region.strip()).order_by("-started_at")
    for row in qs:
        est = timezone.localtime(row.estimated_resolution_at) if row.estimated_resolution_at else None
        outages.append(
            {
                "title": row.title,
                "description": row.description[:500],
                "started_at": timezone.localtime(row.started_at).isoformat(timespec="seconds"),
                "estimated_resolution_at": est.isoformat(timespec="seconds") if est else None,
            }
        )
    return {"intent": "active_outages", "region": account.region, "outages": outages}


def build_chat_context(*, user, intent: str, account: CustomerAccount | None = None) -> dict[str, Any]:
    acct = account if account is not None else get_customer_account_for_user(user)
    match intent:
        case "current_plan":
            return build_plan_context(account=acct)
        case "account_balance":
            ctx = build_balance_context(account=acct)
            return ctx
        case "data_usage":
            ctx = build_usage_context(account=acct)
            return ctx
        case "open_complaints":
            return build_complaints_context(account=acct)
        case "last_payment":
            return build_payment_context(account=acct)
        case "active_outages":
            return build_outage_context(account=acct)
        case _:
            return {"intent": "unsupported"}


def context_has_required_data(intent: str, context: dict[str, Any]) -> bool:
    """Return False when DB context cannot ground an answer safely."""
    if intent == "current_plan":
        return bool(context.get("plan"))
    if intent == "account_balance":
        return context.get("current_balance") is not None
    if intent == "data_usage":
        return bool(context.get("usage"))
    if intent == "open_complaints":
        # Empty list still answers "no open complaints".
        return context.get("complaints") is not None
    if intent == "last_payment":
        return context.get("payment") is not None
    if intent == "active_outages":
        return context.get("region") is not None
    return False
