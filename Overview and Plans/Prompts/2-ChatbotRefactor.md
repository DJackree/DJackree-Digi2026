# Prompt: Chatbot refactor to meet `ProjectDescription.md` (Module 2)

You are a senior Django engineer working on the **Digicel Assessment** repo (`DigicelAssessment/` Django project). Your task is to **plan and implement** chatbot changes so Module 2 fully aligns with **Technical Expectations** in:

- `Overview and Plans/Project Overview/ProjectDescription.md` — **Module 2 — AI Customer Chatbot**

This file is a **hand-off prompt**: follow it in order, keep changes scoped to the chatbot and closely related tests/docs, and do not regress Complaints/Docker/seed behavior unless explicitly required.

---

## 1. Requirements traceability (what must be true)

From `ProjectDescription.md` **Module 2**:

| Requirement | Meaning for implementation |
|-------------|----------------------------|
| Responses use **real DB data** passed as LLM context | Continue building context from ORM; never invent balances/plan names. |
| System prompt: answer **only from provided context**; say when information is insufficient | Strengthen prompts when adding multi-intent / follow-up paths so the model cannot “fill in” missing sections. |
| **Conversation history maintained within a session** | Persist messages (already); ensure **every grounded turn** can use transcript meaningfully—not only a clipped string in one-shot prompts. |
| **Handle follow-up questions naturally** | Intent + context selection must use **recent turns** (user + assistant), not only keyword match on the latest utterance. Short-circuiting to `unsupported` must not block normal follow-ups that refer to prior topic. |
| **Sensitive data**: do not pass unnecessary fields into prompts | When merging contexts, include only fields needed for allowed intents; continue excluding internal complaint notes, raw exception text, etc. |

**Explicit gap in current codebase (for context):**

- `detect_intent()` is single-intent, first-match keyword rules, with a **very narrow** follow-up branch (`intents.py`).
- `post_message` returns canned `unsupported` **before** Groq, so many pragmatic follow-ups never get a model pass.
- `_recent_user_intent()` only looks at **previous user** messages and drops the thread if the last user intent was `unsupported`.
- Groq is called as a **single user blob** (`groq_client.py`); transcript is embedded in text, which is acceptable if intent/context match the user’s actual need.

**Success looks like:** a customer can ask an initial grounded question, then ask “What about the data allowance on that?” / “Can you break that down?” / “And my balance?” without hitting spurious `unsupported`, while **still** enforcing customer scope and context-only answers.

---

## 2. Design goals (non-negotiable)

1. **Grounding first**: No feature may cause the model to answer outside `ACCOUNT_CONTEXT` built from this user’s `CustomerAccount` and related rows.
2. **Customer-only**: Keep `@role_required(UserProfile.Role.CUSTOMER)` and existing access checks; agents/admins stay blocked from `/chatbot/`.
3. **Deterministic safety layer**: Prefer explicit rules for “what data is in play” vs. relying on the LLM to refuse.
4. **Backward compatible API**: Prefer keeping JSON response shape `{ ok, session_id, intent, message }` unless you add **optional** fields (e.g. `intents: [...]`) documented in README.
5. **Tests**: Every behavioral change gets/updates tests in `chatbot/tests.py`; run `python manage.py check` and `python manage.py test chatbot -v 2` with Postgres available.

---

## 3. Proposed architecture (recommended direction)

Implement a **two-stage** pipeline inside `post_message` (conceptually):

### Stage A — “What does this turn need from the database?”

Replace or extend pure keyword intent with **signals** that can combine:

1. **Lexical signals** — existing keyword groups in `detect_intent` / `detect_intents`.
2. **Dialogue state** — derived from the last **N** messages (both roles), e.g.:
   - Last **grounded** user intent (skip `unsupported` user rows by scanning further back, or store “active topic” differently).
   - Last **assistant** intent or a small structured “topic” extracted from persisted assistant `ChatMessage.intent` field (already stored).
3. **Follow-up / coreference heuristic** — e.g. messages that are short questions, contain pronouns (“that”, “it”, “same”, “also”), or are clearly elliptical **and** a recent grounded topic exists → **reuse or merge** intents instead of `unsupported`.

Deliverable: a function such as `resolve_intents_for_turn(text, prior_messages) -> list[str]` or `ResolvedTurn(intents: list[str], rationale: str)` with **documented priority rules** (third-party / neighbor checks still win → `unsupported`).

### Stage B — Context merge + model call

1. **`build_chat_context`** (or new `build_merged_context`) produces one JSON-serializable dict covering **all** resolved intents for this turn (see multi-intent pattern discussed in project chat: merge plan + balance sections without key collisions).
2. **`context_has_required_data`** becomes per-intent AND over merged structure.
3. **Prompt** (`prompts.py`): Update `build_user_prompt` / `build_system_prompt` so that when multiple intents are present, the model must answer **each** part from the correct section; if a section is missing, use the existing “missing information” phrase for **that** part only (word precisely to avoid inventing).

4. **When to skip Groq** — Only skip when:
   - True unsupported / third-party / out-of-scope **after** dialogue resolution; or
   - Missing API key path unchanged; or
   - Validation errors.

   Avoid skipping Groq solely because keywords didn’t match if dialogue state yields a **safe** grounded context.

### Optional (stronger, more work)

- **True multi-turn Groq API**: pass `messages=[...]` with prior turns instead of one concatenated user string. Only do this if you cap tokens, strip sensitive fields, and keep system instructions strict. Not required if Stage A+B fixes acceptance.

---

## 4. File-by-file implementation checklist

### `DigicelAssessment/chatbot/intents.py`

- [ ] Add `detect_intents(message, dialogue_state) -> list[str]` **or** extend `detect_intent` with clear deprecation path.
- [ ] Define ordering / deduplication rules (stable sort for prompt consistency).
- [ ] Expand follow-up detection beyond `yes/no/more` and `len(words) <= 4` using **dialogue_state** (keep false positives low).
- [ ] Ensure **multi-clause** questions (e.g. plan + balance) can return **both** intents when both lexical signals fire (fix “first match wins” where product expects both).
- [ ] Add unit tests for intent resolution tables (strings → expected intent list).

### `DigicelAssessment/chatbot/views.py`

- [ ] Replace single `intent = detect_intent(...)` with resolved intent list (store **primary** intent on `ChatMessage` for backwards compatibility, or add nullable `intents` JSON field—see Models).
- [ ] Fix `_recent_user_intent` / replace with `dialogue_state` builder that considers **assistant** turns and skips **only** unsupported where appropriate (document behavior).
- [ ] Merge contexts before `ask_groq`; single assistant reply summarizing all parts (preferred UX).
- [ ] Review all early returns (`unsupported`, missing info) so they don’t fire incorrectly on follow-ups.

### `DigicelAssessment/chatbot/context.py`

- [ ] Add `merge_contexts(intents: list[str], account) -> dict` composing existing `build_*_context` helpers.
- [ ] Ensure merged dict has unambiguous namespaces (e.g. top-level keys per intent or `{"sections": {...}}`).
- [ ] Extend `context_has_required_data` to validate **each** intent in the resolved list.

### `DigicelAssessment/chatbot/prompts.py`

- [ ] Update system + user instructions for **multi-section** `ACCOUNT_CONTEXT`.
- [ ] Clarify currency labels and which numeric fields are **subscription price** vs **account balance** to reduce LLM confusion.
- [ ] Keep `CHATBOT_RECENT_MESSAGE_COUNT` behavior documented; consider slight increase if needed for follow-ups (watch token limits).

### `DigicelAssessment/chatbot/groq_client.py`

- [ ] If prompt size grows, ensure `max_tokens` / trimming strategy still safe; avoid sending duplicate megabytes of JSON.
- [ ] (Optional) Multi-turn `messages` array—only with red-team style checks for prompt injection via user text.

### `DigicelAssessment/chatbot/models.py` (optional but useful)

- [ ] If analytics matter: add `extra` field e.g. `detected_intents JSONField` or `CharField` comma-list; **or** keep single `intent` as primary and log others only in assistant message `intent` as `multi:primary`—pick one approach and test it.
- [ ] Migrations if schema changes.

### `DigicelAssessment/chatbot/tests.py`

- [ ] Follow-up: initial grounded question → elliptical follow-up → expect **same topic** context used, **not** `unsupported`.
- [ ] Follow-up after assistant used `missing information` / setup reply — define expected behavior and test it.
- [ ] Multi-intent: “balance and plan” → merged context keys present; response not regressing to monthly price as balance (smoke assertion on persisted assistant content or on context builder output).
- [ ] Third-party queries still `unsupported` with **no** extra data leakage.
- [ ] Existing Phase 2/3 tests updated, not deleted, unless obsolete.

### `DigicelAssessment/README.md`

- [ ] Under Chatbot, add **Follow-ups & multi-part questions** — how it works and manual QA steps aligned with `ProjectDescription.md`.

---

## 5. Acceptance criteria (definition of done)

The refactor is complete when:

1. **`ProjectDescription.md` Module 2** bullet on **conversation history / follow-ups** is demonstrably met (manual script + automated tests).
2. **No new leakage**: complaint **descriptions** and internal notes never enter prompts; outages/complaints contexts remain customer-safe.
3. **`python manage.py check`** clean; **`python manage.py test chatbot -v 2`** passes against Postgres.
4. **API contract**: documented if `intent` semantics change (primary vs list); frontend (`chatbot.js`) still works without change unless response JSON extended.
5. **README** updated with reviewer-facing verification for follow-up flows.

---

## 6. Suggested implementation order

1. Add **dialogue state** helper + tests (no Groq).
2. Add **multi-intent** detection + **context merge** + tests.
3. Adjust **views** flow so `unsupported` short-circuit matches new resolution.
4. Update **prompts** for merged context + disambiguation (plan price vs balance).
5. README + full suite run.
6. (Optional) Multi-turn Groq API messages array.

---

## 7. Out of scope (unless you explicitly expand)

- New business intents beyond the six example question families (unless already in `SUPPORTED_INTENTS`).
- Non-customer roles using chatbot.
- Replacing Bootstrap UI or Groq model name mandated by brief (`llama-3.1-8b-instant`).

---

## 8. Reference paths in repo

- Spec: `Overview and Plans/Project Overview/ProjectDescription.md`
- Chat HTTP + persistence: `DigicelAssessment/chatbot/views.py`
- Intent rules: `DigicelAssessment/chatbot/intents.py`
- DB context builders: `DigicelAssessment/chatbot/context.py`
- Prompting: `DigicelAssessment/chatbot/prompts.py`
- Groq wrapper: `DigicelAssessment/chatbot/groq_client.py`
- Tests: `DigicelAssessment/chatbot/tests.py`
- UI: `DigicelAssessment/templates/chatbot/chat.html`, `DigicelAssessment/chatbot/static/chatbot/chatbot.js`

Use this document as the **single source of intent** for the refactor PR or implementation pass named **ChatbotRefactor**.
