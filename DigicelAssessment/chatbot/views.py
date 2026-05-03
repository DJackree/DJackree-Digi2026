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

from chatbot.context import build_chat_context, context_has_required_data
from chatbot.groq_client import (
    ChatbotGroqBadResponse,
    ChatbotGroqMisconfigured,
    ChatbotGroqTransientError,
    ask_groq,
)
from chatbot.intents import detect_intent
from chatbot.models import ChatMessage, ChatSession
from chatbot.prompts import (
    MISSING_API_KEY_REPLY,
    MISSING_INFORMATION_PHRASE,
    SERVICE_TEMPORARILY_UNAVAILABLE_REPLY,
    UNSUPPORTED_USER_QUESTION_REPLY,
)
from customers.services import get_customer_account_for_user


def _json_errors(status: int, payload: dict) -> JsonResponse:
    body = dict(payload)
    body.setdefault("ok", False)
    return JsonResponse(body, status=status)


def _recent_user_intent(messages: list[ChatMessage]) -> str | None:
    for msg in reversed(messages):
        if msg.role == ChatMessage.Role.USER and (msg.intent or "").strip():
            if msg.intent == "unsupported":
                return None
            return msg.intent
    return None


def _latest_session(request) -> ChatSession | None:
    return (
        ChatSession.objects.filter(user=request.user)
        .order_by("-updated_at", "-pk")
        .first()
    )


def _get_or_create_latest_session(request) -> ChatSession:
    existing = _latest_session(request)
    if existing:
        return existing
    return ChatSession.objects.create(user=request.user)


def _touch_session(session: ChatSession) -> None:
    session.updated_at = timezone.now()
    session.save(update_fields=["updated_at"])


def _sanitize_assistant_reply(text: str, max_chars: int = 4000) -> str:
    text = text.strip().replace("\r\n", "\n")
    return text[:max_chars]


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
                "messages": [],
                "session": None,
                "max_chars": getattr(settings, "CHATBOT_MESSAGE_MAX_LENGTH", 1000),
            },
        )

    session = _get_or_create_latest_session(request)
    messages = list(session.messages.order_by("created_at"))
    return render(
        request,
        "chatbot/chat.html",
        {
            "no_account": False,
            "session": session,
            "messages": messages,
            "max_chars": getattr(settings, "CHATBOT_MESSAGE_MAX_LENGTH", 1000),
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
    recent_hint = _recent_user_intent(prior)
    intent = detect_intent(text, recent_intent=recent_hint)

    ChatMessage.objects.create(
        session=session,
        role=ChatMessage.Role.USER,
        content=text,
        intent=intent,
    )
    _touch_session(session)
    transcripts = list(session.messages.order_by("created_at"))

    if intent == "unsupported":
        assistant_text = UNSUPPORTED_USER_QUESTION_REPLY
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=assistant_text,
            intent=intent,
        )
        _touch_session(session)
        return JsonResponse({"ok": True, "session_id": session.pk, "intent": intent, "message": assistant_text})

    context = build_chat_context(user=request.user, intent=intent, account=account)
    if not context_has_required_data(intent, context):
        assistant_text = MISSING_INFORMATION_PHRASE
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=assistant_text,
            intent=intent,
        )
        _touch_session(session)
        return JsonResponse({"ok": True, "session_id": session.pk, "intent": intent, "message": assistant_text})

    if not getattr(settings, "GROQ_API_KEY", None):
        assistant_text = MISSING_API_KEY_REPLY
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=assistant_text,
            intent=intent,
        )
        _touch_session(session)
        return JsonResponse({"ok": True, "session_id": session.pk, "intent": intent, "message": assistant_text})

    currency = getattr(settings, "CHATBOT_DEFAULT_CURRENCY", "JMD")

    assistant_text = ""
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
        intent=intent,
    )
    _touch_session(session)

    return JsonResponse({"ok": True, "session_id": session.pk, "intent": intent, "message": assistant_text})


@role_required(UserProfile.Role.CUSTOMER)
@require_POST
def new_session(request):
    account = get_customer_account_for_user(request.user)
    if account is None:
        return _json_errors(400, {"detail": "No customer account is linked to your user.", "errors": {"account": ""}})

    sess = ChatSession.objects.create(user=request.user, title="")
    return JsonResponse({"ok": True, "session_id": sess.pk})
