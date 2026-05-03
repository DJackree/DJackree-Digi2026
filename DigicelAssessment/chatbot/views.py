"""Chatbot HTTP handlers (deterministic intents + grounded Groq)."""

from __future__ import annotations

import json

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST

from accounts.decorators import role_required
from accounts.models import UserProfile

from chatbot.context import (
    build_merged_chat_context,
    merged_context_has_required_data,
)
from chatbot.groq_client import (
    ChatbotGroqBadResponse,
    ChatbotGroqMisconfigured,
    ChatbotGroqTransientError,
    ask_groq,
)
from chatbot.intents import detect_intents, dialogue_state_from_messages
from chatbot.models import ChatMessage, ChatSession
from chatbot.prompts import (
    MISSING_API_KEY_REPLY,
    MISSING_INFORMATION_PHRASE,
    SERVICE_TEMPORARILY_UNAVAILABLE_REPLY,
    UNSUPPORTED_USER_QUESTION_REPLY,
    strip_leaked_prompt_echo,
)
from customers.services import get_customer_account_for_user

CHATBOT_SUGGESTED_QUESTIONS = [
    "What plan am I currently on?",
    "What plans are available?",
    "What is my current account balance?",
    "How much data have I used this month?",
    "Do I have any open complaints?",
    "When was my last payment made?",
    "Are there outages affecting my area?",
    "Is there a cheaper plan than what I have?",
]


def _json_errors(status: int, payload: dict) -> JsonResponse:
    body = dict(payload)
    body.setdefault("ok", False)
    return JsonResponse(body, status=status)


def _resolve_customer_chat_session(request) -> ChatSession:
    """Return session from ``?session=`` when valid; else freshest by ``updated_at``; else create."""
    owned = ChatSession.objects.filter(user=request.user)
    param = (request.GET.get("session") or "").strip()
    if param.isdigit():
        selected = owned.filter(pk=int(param)).first()
        if selected is not None:
            return selected

    newest = owned.order_by("-updated_at", "-pk").first()
    if newest is not None:
        return newest

    return ChatSession.objects.create(user=request.user)


def _touch_session(session: ChatSession) -> None:
    session.updated_at = timezone.now()
    session.save(update_fields=["updated_at"])


def _sanitize_assistant_reply(text: str, max_chars: int = 4000) -> str:
    text = strip_leaked_prompt_echo(text)
    text = text.strip().replace("\r\n", "\n")
    return text[:max_chars]


def _deterministic_plan_catalog_price_reply(question: str, context: dict, currency: str) -> str | None:
    """
    Avoid LLM arithmetic errors for cheaper/pricier questions when the answer is fully determined
    by ``plan_catalog.comparison``.
    """
    sections = context.get("sections") or {}
    if len(sections) != 1 or "plan_catalog" not in sections:
        return None
    comp = (sections.get("plan_catalog") or {}).get("comparison") or {}
    yname = comp.get("your_plan_name")
    yprice = comp.get("your_monthly_price")
    if not yname or yprice is None:
        return None
    q = question.lower()
    asks_cheaper = any(
        p in q
        for p in (
            "cheaper",
            "less expensive",
            "lower price",
            "cost less",
            "pay less",
            "lower tier",
        )
    )
    asks_pricier = any(
        p in q
        for p in (
            "more expensive",
            "pricier",
            "higher price",
            "cost more",
            "pay more",
            "higher tier",
        )
    )
    if not asks_cheaper and not asks_pricier:
        return None
    lower = comp.get("plans_with_lower_monthly_price_than_yours") or []
    higher = comp.get("plans_with_higher_monthly_price_than_yours") or []
    if asks_cheaper:
        if lower:
            listed = ", ".join(
                f"{p['name']} ({currency} {p['monthly_price']}/month)" for p in lower
            )
            return (
                f"Yes — these listed plans have a lower monthly price than yours "
                f"({yname}, {currency} {yprice}/month): {listed}."
            )
        if comp.get("cheapest_plan_name") == yname:
            return (
                f"You're on {yname} ({currency} {yprice}/month), which is already the lowest monthly-price "
                "plan in our catalog — there isn't a cheaper plan listed."
            )
    if asks_pricier:
        if higher:
            listed = ", ".join(
                f"{p['name']} ({currency} {p['monthly_price']}/month)" for p in higher
            )
            return (
                f"Yes — these listed plans have a higher monthly price than yours "
                f"({yname}, {currency} {yprice}/month): {listed}."
            )
        if comp.get("priciest_plan_name") == yname:
            return (
                f"You're on {yname} ({currency} {yprice}/month), the highest monthly-price plan in our catalog — "
                "there isn't a more expensive plan listed."
            )
    return None


@role_required(UserProfile.Role.CUSTOMER)
@ensure_csrf_cookie
@require_http_methods(["GET", "HEAD"])
def chat_home(request):
    account = get_customer_account_for_user(request.user)
    if account is None:
        return render(
            request,
            "chatbot/chat.html",
            {
                "no_account": True,
                "chat_messages": [],
                "session": None,
                "max_chars": getattr(settings, "CHATBOT_MESSAGE_MAX_LENGTH", 1000),
            },
        )

    session = _resolve_customer_chat_session(request)
    chat_messages = list(session.messages.order_by("created_at"))
    return render(
        request,
        "chatbot/chat.html",
        {
            "no_account": False,
            "session": session,
            "chat_messages": chat_messages,
            "max_chars": getattr(settings, "CHATBOT_MESSAGE_MAX_LENGTH", 1000),
            "suggested_questions": CHATBOT_SUGGESTED_QUESTIONS,
        },
    )


@role_required(UserProfile.Role.CUSTOMER)
@require_POST
def post_message(request):
    account = get_customer_account_for_user(request.user)
    if account is None:
        return _json_errors(400, {"detail": "No customer account is linked to your user.", "errors": {"account": ""}})

    raw = request.body.decode("utf-8") if request.body else "{}"
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return _json_errors(400, {"detail": "Invalid JSON body.", "errors": {"body": "Invalid JSON."}})

    if not isinstance(payload, dict):
        return _json_errors(400, {"detail": "JSON object required.", "errors": {"body": "Must be an object."}})

    session_id_raw = payload.get("session_id", None)
    message_body = payload.get("message", None)

    if session_id_raw in ("", None):
        return _json_errors(400, {"errors": {"session_id": "This field is required."}})
    try:
        session_pk = int(session_id_raw)
    except (TypeError, ValueError):
        return _json_errors(400, {"errors": {"session_id": "Must be an integer."}})

    session = ChatSession.objects.filter(pk=session_pk, user=request.user).first()
    if session is None:
        return JsonResponse({"detail": "Session not found.", "ok": False}, status=404)

    if not isinstance(message_body, str):
        return _json_errors(400, {"errors": {"message": "Must be a string."}})
    text = message_body.strip()
    if not text:
        return _json_errors(400, {"errors": {"message": "This field may not be blank."}})

    maxlen = getattr(settings, "CHATBOT_MESSAGE_MAX_LENGTH", 1000)
    if len(text) > maxlen:
        return _json_errors(
            400,
            {
                "errors": {
                    "message": f"Message exceeds maximum length ({maxlen} characters).",
                },
            },
        )

    prior = list(session.messages.order_by("created_at"))
    dialogue_state = dialogue_state_from_messages(prior)
    intents = detect_intents(text, dialogue_state)
    primary_intent = intents[0] if intents else "unsupported"

    ChatMessage.objects.create(
        session=session,
        role=ChatMessage.Role.USER,
        content=text,
        intent=primary_intent,
    )
    _touch_session(session)
    transcripts = list(session.messages.order_by("created_at"))

    if primary_intent == "unsupported":
        assistant_text = UNSUPPORTED_USER_QUESTION_REPLY
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=assistant_text,
            intent=primary_intent,
        )
        _touch_session(session)
        return JsonResponse(
            {
                "ok": True,
                "session_id": session.pk,
                "intent": primary_intent,
                "intents": [],
                "message": assistant_text,
            }
        )

    grounded = [ink for ink in intents if ink != "unsupported"]
    context = build_merged_chat_context(user=request.user, intents=grounded, account=account)
    if not merged_context_has_required_data(grounded, context):
        assistant_text = MISSING_INFORMATION_PHRASE
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=assistant_text,
            intent=primary_intent,
        )
        _touch_session(session)
        return JsonResponse(
            {
                "ok": True,
                "session_id": session.pk,
                "intent": primary_intent,
                "intents": grounded,
                "message": assistant_text,
            }
        )

    if not getattr(settings, "GROQ_API_KEY", None):
        assistant_text = MISSING_API_KEY_REPLY
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=assistant_text,
            intent=primary_intent,
        )
        _touch_session(session)
        return JsonResponse(
            {
                "ok": True,
                "session_id": session.pk,
                "intent": primary_intent,
                "intents": grounded,
                "message": assistant_text,
            }
        )

    currency = getattr(settings, "CHATBOT_DEFAULT_CURRENCY", "JMD")

    assistant_text = ""
    deterministic = _deterministic_plan_catalog_price_reply(text, context, currency)
    if deterministic:
        assistant_text = _sanitize_assistant_reply(deterministic)
    else:
        try:
            assistant_reply = ask_groq(
                question=text,
                context=context,
                recent_messages=transcripts,
                currency_code=currency,
            )
            assistant_text = _sanitize_assistant_reply(assistant_reply)
        except ChatbotGroqMisconfigured:
            assistant_text = MISSING_API_KEY_REPLY
        except (ChatbotGroqTransientError, ChatbotGroqBadResponse):
            assistant_text = SERVICE_TEMPORARILY_UNAVAILABLE_REPLY
        except Exception:
            assistant_text = SERVICE_TEMPORARILY_UNAVAILABLE_REPLY

    if not assistant_text:
        assistant_text = SERVICE_TEMPORARILY_UNAVAILABLE_REPLY
    ChatMessage.objects.create(
        session=session,
        role=ChatMessage.Role.ASSISTANT,
        content=assistant_text,
        intent=primary_intent,
    )
    _touch_session(session)

    return JsonResponse(
        {
            "ok": True,
            "session_id": session.pk,
            "intent": primary_intent,
            "intents": grounded,
            "message": assistant_text,
        }
    )


@role_required(UserProfile.Role.CUSTOMER)
@require_POST
def new_session(request):
    account = get_customer_account_for_user(request.user)
    if account is None:
        return _json_errors(400, {"detail": "No customer account is linked to your user.", "errors": {"account": ""}})

    sess = ChatSession.objects.create(user=request.user, title="")
    return JsonResponse({"ok": True, "session_id": sess.pk})
