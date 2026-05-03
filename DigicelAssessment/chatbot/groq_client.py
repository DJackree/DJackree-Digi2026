"""Call Groq's chat API with strict prompts built from database-backed context.

Errors are turned into small exception types so HTTP views can show friendly text
without leaking raw vendor error bodies to end users.
"""

from __future__ import annotations

from django.conf import settings

from chatbot.prompts import build_system_prompt, build_user_prompt


class ChatbotGroqError(Exception):
    """Base error for failing to obtain a grounded assistant reply."""


class ChatbotGroqMisconfigured(ChatbotGroqError):
    """Groq credentials missing."""

    code = "missing_api_key"


class ChatbotGroqTransientError(ChatbotGroqError):
    """Upstream connectivity or rate-limit style failures."""

    code = "transient_upstream"


class ChatbotGroqBadResponse(ChatbotGroqError):
    """Malformed or empty upstream response."""

    code = "bad_upstream_response"


def ask_groq(*, question: str, context: dict, recent_messages, currency_code: str) -> str:
    """Send one chat completion request and return the assistant's text reply.

    ``context`` is the JSON built in ``chatbot.context`` (facts only). Recent
    transcript lines help the model understand short follow-ups like "what about last month?".
    """

    api_key = getattr(settings, "GROQ_API_KEY", None)
    if not api_key:
        raise ChatbotGroqMisconfigured("GROQ_API_KEY is missing.")

    # Import lazily so management commands/tests can load without grpc noise in some setups.
    import groq
    from groq import Groq

    timeout = getattr(settings, "GROQ_TIMEOUT_SECONDS", 30.0)

    client = Groq(api_key=api_key, timeout=timeout)

    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(
        question=question,
        context=context,
        recent_messages=list(recent_messages),
        currency_code=currency_code,
    )

    model = getattr(settings, "GROQ_MODEL", "llama-3.1-8b-instant")
    max_completion_tokens = getattr(settings, "GROQ_MAX_COMPLETION_TOKENS", 512)

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0.1,
            max_tokens=max_completion_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except (
        groq.APIConnectionError,  # includes APITimeoutError in this SDK
        groq.APIStatusError,  # includes RateLimitError subclasses
    ) as exc:  # type: ignore[attr-defined]
        raise ChatbotGroqTransientError("Groq upstream error.") from exc

    try:
        choices = getattr(response, "choices", None) or []
        if not choices:
            raise ChatbotGroqBadResponse("Empty Groq choices.")
        msg = getattr(choices[0], "message", None)
        content = (getattr(msg, "content", None) if msg else None) or ""
    except ChatbotGroqBadResponse:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ChatbotGroqBadResponse("Malformed Groq response.") from exc

    content = content.strip()
    if not content:
        raise ChatbotGroqBadResponse("Empty assistant content.")
    return content
