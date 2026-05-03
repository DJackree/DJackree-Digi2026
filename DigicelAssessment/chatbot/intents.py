"""Rule-based intent detection for the AI customer chatbot."""

from __future__ import annotations

import re


SUPPORTED_INTENTS = frozenset(
    {
        "current_plan",
        "account_balance",
        "data_usage",
        "open_complaints",
        "last_payment",
        "active_outages",
        "unsupported",
    }
)


def _normalize_text(message: str) -> str:
    text = message.lower().strip()
    text = re.sub(r"[^\w\s]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def detect_intent(message: str, recent_intent: str | None = None) -> str:
    """Map free text to a single intent keyword; deterministic first-hit keyword groups."""
    text = _normalize_text(message)
    words = frozenset(text.split())

    third_party = frozenset(
        {"neighbor", "neighbour", "cousin", "friend", "somebody", "anyone"}
    )
    if third_party.intersection(words):
        return "unsupported"

    if any(w in words for w in ("plan", "package", "allowance")) or "monthly" in words:
        return "current_plan"
    if any(w in words for w in ("balance", "owe", "bill", "amount", "due")):
        return "account_balance"
    if "data" in words and ("gb" in words or "gigabyte" in text or "gigabytes" in text):
        return "data_usage"
    if "how" in words and "much" in words and ("data" in words or "usage" in words):
        return "data_usage"
    if "usage" in words and "used" in words:
        return "data_usage"
    if any(w in words for w in ("complaint", "complaints", "ticket", "tickets", "case", "cases")):
        return "open_complaints"
    if "payment" in words or "paid" in words:
        return "last_payment"
    if any(w in words for w in ("outage", "fault", "network", "area", "service", "down")):
        return "active_outages"

    # Light follow-up hint only (does not broaden data access without prior intent).
    if recent_intent in SUPPORTED_INTENTS and recent_intent != "unsupported":
        followups = ("yes", "no", "ok", "thanks", "thank", "more", "details", "again", "confirm")
        if any(w in words for w in followups) and len(words) <= 4:
            return recent_intent

    return "unsupported"
