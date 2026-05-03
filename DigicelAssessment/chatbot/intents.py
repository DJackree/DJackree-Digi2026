"""Rule-based intent detection for the AI customer chatbot."""

from __future__ import annotations

import re
from dataclasses import dataclass

SUPPORTED_INTENTS = frozenset(
    {
        "plan_catalog",
        "current_plan",
        "account_balance",
        "data_usage",
        "open_complaints",
        "last_payment",
        "active_outages",
        "unsupported",
    }
)

GROUNDED_ONLY = frozenset(SUPPORTED_INTENTS - {"unsupported"})

INTENT_MERGE_PRIORITY = (
    "plan_catalog",
    "current_plan",
    "account_balance",
    "data_usage",
    "open_complaints",
    "last_payment",
    "active_outages",
)


def _intent_sort_key(intent: str) -> int:
    try:
        return INTENT_MERGE_PRIORITY.index(intent)
    except ValueError:
        return 999


def _normalize_text(message: str) -> str:
    text = message.lower().strip()
    text = re.sub(r"[^\w\s]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


@dataclass(frozen=True)
class DialogueState:
    """Recent grounded-topic hint from prior transcript (user + assistant)."""

    last_grounded_intent: str | None


def dialogue_state_from_messages(messages: list) -> DialogueState:
    """Newest grounded intent walking backward; unsupported turns do not erase prior topic."""
    for msg in reversed(messages):
        ink = (msg.intent or "").strip()
        if not ink or ink == "unsupported":
            continue
        if ink in GROUNDED_ONLY:
            return DialogueState(last_grounded_intent=ink)
    return DialogueState(last_grounded_intent=None)


def _third_party_trigger(words: frozenset[str]) -> bool:
    return bool(
        frozenset(
            {"neighbor", "neighbour", "cousin", "friend", "somebody", "anyone"}
        ).intersection(words)
    )


def _wants_plan_catalog(words: frozenset[str], text: str) -> bool:
    """Listing all plans or comparing tiers/prices (not the same as *your* plan only)."""
    has_plan_word = (
        "plan" in words
        or "plans" in words
        or "package" in words
        or "packages" in words
    )
    if not has_plan_word:
        return False
    if "plans" in words and (words & frozenset(("all", "every", "available", "list", "show", "other"))):
        return True
    if "plan" in words and "available" in words:
        return True
    if "every" in words and "plan" in words:
        return True
    if "which" in words and ("plan" in words or "plans" in words):
        return True
    if words & frozenset(("cheaper", "expensive", "upgrade", "downgrade", "compare", "comparison")):
        return True
    if "cost" in words and (words & frozenset(("more", "less"))):
        return True
    if (words & frozenset(("higher", "lower", "high", "low"))) and has_plan_word:
        return True
    if (words & frozenset(("better", "best"))) and has_plan_word:
        return True
    if (words & frozenset(("option", "options"))) and has_plan_word:
        return True
    return False


def _keep_both_current_plan_and_catalog(words: frozenset[str]) -> bool:
    """User explicitly asked for *their* plan AND a full listing (keep both contexts)."""
    my = (
        ("my" in words or "i" in words or "mine" in words or "our" in words)
        and ("plan" in words or "plans" in words)
    )
    catalogish = bool(
        words & frozenset(("all", "every", "available", "list", "show", "other", "catalog", "offered", "offer"))
    )
    return my and catalogish


def _dedupe_catalog_vs_current(intents: list[str], words: frozenset[str]) -> list[str]:
    """`plan_catalog` already includes ``your_plan``; drop redundant ``current_plan`` when appropriate."""
    if "plan_catalog" not in intents or "current_plan" not in intents:
        return intents
    if _keep_both_current_plan_and_catalog(words):
        return intents
    return [i for i in intents if i != "current_plan"]


def _lexical_intents(words: frozenset[str], text: str) -> list[str]:
    """Collect every intent whose keyword rules match this turn."""
    intents: list[str] = []

    def add(name: str) -> None:
        if name not in intents:
            intents.append(name)

    if _wants_plan_catalog(words, text):
        add("plan_catalog")
    if any(w in words for w in ("plan", "package", "allowance")) or "monthly" in words:
        add("current_plan")
    if any(w in words for w in ("balance", "owe", "bill", "amount", "due")):
        add("account_balance")
    # Compare used vs allowance — needs metered usage, not plan section alone.
    if "data" in words and (
        any(
            w in words
            for w in (
                "over",
                "exceeded",
                "past",
                "remaining",
                "left",
                "limit",
                "cap",
                "used",
                "usage",
            )
        )
        or ("allowance" in words and any(w in words for w in ("over", "exceeded", "used", "usage", "remaining", "left")))
    ):
        add("data_usage")
    if "data" in words and ("gb" in words or "gigabyte" in text or "gigabytes" in text):
        add("data_usage")
    if "how" in words and "much" in words and ("data" in words or "usage" in words):
        add("data_usage")
    if "usage" in words and "used" in words:
        add("data_usage")
    if "usage" in words:
        add("data_usage")
    if any(w in words for w in ("complaint", "complaints", "ticket", "tickets", "case", "cases")):
        add("open_complaints")
    if "payment" in words or "payments" in words or "paid" in words:
        add("last_payment")
    if any(w in words for w in ("outage", "outages", "fault", "faults")):
        add("active_outages")
    elif "network" in words or "internet" in words or "dsl" in words or "fiber" in words:
        if "down" in words or "offline" in words or "slow" in words or "degraded" in words:
            add("active_outages")
    elif "service" in words and any(w in words for w in ("down", "offline", "out")):
        add("active_outages")
    elif "area" in words and any(w in words for w in ("outage", "fault")):
        add("active_outages")

    intents = _dedupe_catalog_vs_current(intents, words)
    return sorted(intents, key=_intent_sort_key)


def _looks_dialogue_followup(words: frozenset[str], text: str, state: DialogueState) -> bool:
    """Elliptical continuation when a grounded topic exists and lexical rules failed."""
    if not state.last_grounded_intent:
        return False
    wc = len(words)
    # Avoid broad reuse on long free-text.
    if wc > 16:
        return False

    shorts = frozenset(
        (
            "yes",
            "no",
            "ok",
            "okay",
            "thanks",
            "thank",
            "more",
            "details",
            "detail",
            "again",
            "confirm",
            "sure",
        )
    )
    if bool(words & shorts) and wc <= 4:
        return True

    cues = frozenset(
        (
            "that",
            "it",
            "same",
            "also",
            "those",
            "these",
            "why",
            "explain",
            "clarify",
            "expand",
            "elaborate",
        )
    )
    if words & cues and wc <= 10:
        return True

    if "break" in words and wc <= 10:
        return True
    if "what" in words and "about" in words and wc <= 12:
        return True
    if "how" in words and "about" in words and wc <= 12:
        return True

    ack = ("thanks", "thank", "perfect", "got", "understood")
    if wc <= 5 and bool(words & frozenset(ack)):
        return True

    return False


def detect_intents(message: str, dialogue_state: DialogueState | None = None) -> list[str]:
    """Return one or more grounded intents or ``['unsupported']`` for this customer turn."""

    dialogue_state = dialogue_state or DialogueState(last_grounded_intent=None)
    text = _normalize_text(message)
    words = frozenset(text.split())

    if _third_party_trigger(words):
        return ["unsupported"]

    lexical = _lexical_intents(words, text)
    if lexical:
        return lexical

    if _looks_dialogue_followup(words, text, dialogue_state):
        topic = dialogue_state.last_grounded_intent
        if topic:
            return [topic]

    return ["unsupported"]


def detect_intent(message: str, recent_intent: str | None = None) -> str:
    """Map free text to a single primary intent; ``recent_intent`` is backward compatible."""
    state = DialogueState(last_grounded_intent=recent_intent)
    found = detect_intents(message, state)
    return found[0] if found else "unsupported"
