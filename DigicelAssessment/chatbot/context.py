"""Build JSON "context" snippets the chatbot may use when calling Groq.

Each user question is classified into one or more *intents* (plan, balance, etc.).
This module loads only the database rows needed for those intents and turns them
into plain dictionaries. The LLM is instructed to answer *only* from this JSON,
so we never dump the whole customer record into the prompt.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.utils import timezone

from complaints.models import Complaint
from customers.models import AccountUsage, CustomerAccount, Payment, ServicePlan
from customers.services import get_customer_account_for_user
from network.models import NetworkOutage

GROUNDED_CHAT_INTENTS = frozenset(
    {
        "plan_catalog",
        "current_plan",
        "account_balance",
        "data_usage",
        "open_complaints",
        "last_payment",
        "active_outages",
    }
)


def _intent_sort_key(intent: str) -> int:
    order = (
        "plan_catalog",
        "current_plan",
        "account_balance",
        "data_usage",
        "open_complaints",
        "last_payment",
        "active_outages",
    )
    try:
        return order.index(intent)
    except ValueError:
        return 999


OPEN_STATUSES = {
    Complaint.Status.OPEN,
    Complaint.Status.IN_PROGRESS,
    Complaint.Status.ESCALATED,
}


def _money_str(amount: Decimal) -> str:
    return f"{amount.quantize(Decimal('0.01'))}"


def build_plan_catalog_context(*, account: CustomerAccount | None) -> dict[str, Any]:
    """All retail service plans for listing / price-tier comparison (plus the customer's current plan)."""
    qs = list(ServicePlan.objects.all().order_by("monthly_price", "name"))
    rows: list[dict[str, Any]] = []
    for p in qs:
        rows.append(
            {
                "name": p.name,
                "monthly_price": _money_str(p.monthly_price),
                "data_allowance_gb": _money_str(p.data_allowance_gb),
                "call_minutes": p.call_minutes,
                "sms_allowance": p.sms_allowance,
            }
        )
    your_plan = None
    if account is not None:
        your_plan = build_plan_context(account=account).get("plan")

    comparison: dict[str, Any]
    if rows:
        comparison = {
            "cheapest_plan_name": rows[0]["name"],
            "cheapest_monthly_price": rows[0]["monthly_price"],
            "priciest_plan_name": rows[-1]["name"],
            "priciest_monthly_price": rows[-1]["monthly_price"],
        }
    else:
        comparison = {
            "cheapest_plan_name": None,
            "cheapest_monthly_price": None,
            "priciest_plan_name": None,
            "priciest_monthly_price": None,
        }

    if your_plan:
        yp = Decimal(your_plan["monthly_price"])
        comparison["your_plan_name"] = your_plan["name"]
        comparison["your_monthly_price"] = your_plan["monthly_price"]
        lower: list[dict[str, str]] = []
        higher: list[dict[str, str]] = []
        for row in rows:
            rp = Decimal(row["monthly_price"])
            if rp < yp:
                lower.append({"name": row["name"], "monthly_price": row["monthly_price"]})
            elif rp > yp:
                higher.append({"name": row["name"], "monthly_price": row["monthly_price"]})
        comparison["plans_with_lower_monthly_price_than_yours"] = lower
        comparison["plans_with_higher_monthly_price_than_yours"] = higher
    else:
        comparison["your_plan_name"] = None
        comparison["your_monthly_price"] = None
        comparison["plans_with_lower_monthly_price_than_yours"] = []
        comparison["plans_with_higher_monthly_price_than_yours"] = []

    return {
        "intent": "plan_catalog",
        "your_plan": your_plan,
        "plans": rows,
        "by_price_low_to_high": [p.name for p in qs],
        "comparison": comparison,
    }


def build_plan_context(*, account: CustomerAccount | None) -> dict[str, Any]:
    """Named fields for the subscriber's current service tier (or empty if no account)."""

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
    """How much the account owes or is in credit (string dollars for stable LLM formatting)."""

    if account is None:
        return {"intent": "account_balance", "current_balance": None}
    return {
        "intent": "account_balance",
        "current_balance": _money_str(account.current_balance),
    }


def _current_usage_record(account: CustomerAccount) -> AccountUsage | None:
    """Pick the usage row covering "today" if possible, else the most recent period on file."""

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
    """Data/minute/SMS consumption for the active billing slice plus plan allowance cap."""

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
    """Short list of non-terminal complaints for this account (reference, type, status)."""

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
    """Most recent payment amount and date, if any payments exist."""

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
    """Active outage rows in the customer's home region (case-insensitive match)."""

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
    """Dispatch table: pick the right builder for one intent string."""

    acct = account if account is not None else get_customer_account_for_user(user)
    match intent:
        case "plan_catalog":
            return build_plan_catalog_context(account=acct)
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


def build_merged_chat_context(
    *,
    user,
    intents: list[str],
    account: CustomerAccount | None = None,
) -> dict[str, Any]:
    """
    Bundle several intent snippets for one chat turn.

    Groq receives a single JSON blob. When the customer mixes topics ("balance and
    outages"), we list each intent under ``sections`` so the model answers every part.
    """

    acct = account if account is not None else get_customer_account_for_user(user)
    unique = sorted(
        [i for i in dict.fromkeys(intents) if i in GROUNDED_CHAT_INTENTS],
        key=_intent_sort_key,
    )
    sections: dict[str, dict[str, Any]] = {}
    for ink in unique:
        sections[ink] = dict(build_chat_context(user=user, intent=ink, account=acct))

    return {
        "multi": len(unique) > 1,
        "intents": unique,
        "sections": sections,
    }


def merged_context_has_required_data(intents: list[str], merged: dict[str, Any]) -> bool:
    """Require every grounded intent passed to Groq (or deterministic reply) has sufficient DB."""
    secs = merged.get("sections") or {}
    for ink in intents:
        if ink not in GROUNDED_CHAT_INTENTS:
            continue
        snippet = secs.get(ink)
        if not snippet:
            return False
        if not context_has_required_data(ink, snippet):
            return False
    return True


def context_has_required_data(intent: str, context: dict[str, Any]) -> bool:
    """Return False if the database did not give enough fields to answer safely."""

    if intent == "plan_catalog":
        return bool(context.get("plans"))
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
