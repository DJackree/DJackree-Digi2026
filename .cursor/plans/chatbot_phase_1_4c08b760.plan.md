---
name: chatbot phase 1
overview: Implement the chatbot database foundation by adding a new Django app with chat session/message persistence, admin inspection, migration coverage, and verification that existing seeded customer data supports the planned chatbot intents.
todos:
  - id: scaffold-chatbot-app
    content: Scaffold the `chatbot` Django app and register it in settings.
    status: completed
  - id: add-chatbot-models
    content: Implement `ChatSession` and `ChatMessage` models with indexes and migrations.
    status: completed
  - id: register-chatbot-admin
    content: Add Django admin registration for chat sessions and messages.
    status: completed
  - id: verify-seed-dependencies
    content: Confirm existing seeded account, complaint, payment, usage, and outage data supports chatbot Phase 2 intents without seeding fake transcripts.
    status: completed
  - id: add-tests-and-docs
    content: Add focused chatbot model tests and README notes, then run Django checks/tests.
    status: completed
isProject: false
---

# Chatbot Phase 1 Database Plan

## Scope
Implement only Phase 1 of [`Overview and Plans/Plans/03-ai-customer-chatbot-plan.md`](Overview%20and%20Plans/Plans/03-ai-customer-chatbot-plan.md): app scaffolding, persistence models, admin registration, migration, and seed-data dependency verification. Do not add chatbot routes, Groq calls, intent detection, prompts, templates, or navbar links yet.

## Target Shape
Create a new [`DigicelAssessment/chatbot/`](DigicelAssessment/chatbot/) Django app and register it in [`DigicelAssessment/config/settings.py`](DigicelAssessment/config/settings.py). The app will own only chat transcript persistence:

```python
class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chat_sessions")
    title = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

```python
class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    intent = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

Add indexes for recent session lookup and chronological transcript lookup:

```python
models.Index(fields=["user", "-updated_at"])
models.Index(fields=["session", "created_at"])
```

## Implementation Steps
1. Scaffold [`DigicelAssessment/chatbot/`](DigicelAssessment/chatbot/) with standard app files: `apps.py`, `models.py`, `admin.py`, `tests.py`, and `migrations/__init__.py`.
2. Add `"chatbot"` to `INSTALLED_APPS` in [`DigicelAssessment/config/settings.py`](DigicelAssessment/config/settings.py), near the existing project apps.
3. Implement `ChatSession` and `ChatMessage` in [`DigicelAssessment/chatbot/models.py`](DigicelAssessment/chatbot/models.py), including `Role` choices (`user`, `assistant`), `__str__` methods, sensible ordering if useful, and the planned indexes.
4. Register both models in [`DigicelAssessment/chatbot/admin.py`](DigicelAssessment/chatbot/admin.py) using the same conventions as [`DigicelAssessment/complaints/admin.py`](DigicelAssessment/complaints/admin.py): `list_display`, `list_filter`, `search_fields`, `autocomplete_fields`, `date_hierarchy`, and read-only timestamps.
5. Generate the initial migration for `chatbot` and inspect it to confirm it contains only the two chatbot tables and indexes.
6. Leave [`DigicelAssessment/core/management/commands/seed_data.py`](DigicelAssessment/core/management/commands/seed_data.py) functionally unchanged unless verification shows a missing dependency. The current seed already creates customer accounts, service plans, usage, payments, open complaints, and an active Kingston outage for `customer1`; no fake chat transcripts should be seeded.
7. Add focused model tests in [`DigicelAssessment/chatbot/tests.py`](DigicelAssessment/chatbot/tests.py) for session/message creation, cascade deletion, role choices, and query ordering/index assumptions at the ORM level.
8. Update [`DigicelAssessment/README.md`](DigicelAssessment/README.md) with a short Phase 1 note: chatbot migrations/admin exist, no chat data is seeded, and later phases require `GROQ_API_KEY` but Phase 1 does not store secrets in the DB.

## Verification
Run from [`DigicelAssessment/`](DigicelAssessment/):

```bash
python manage.py makemigrations chatbot
python manage.py migrate
python manage.py check
python manage.py test chatbot
```

Also run a quick shell or admin smoke check to confirm seeded dependencies exist for all planned Phase 2 intents: current plan, balance, current-period usage, last payment, open complaints, and active region outage.

## Acceptance Criteria
- `chatbot` is registered and migrations apply cleanly.
- `ChatSession` and `ChatMessage` records can be created and inspected in Django admin.
- Chat messages are cascaded when their session is deleted.
- No Groq API keys, prompts, raw context payloads, or unnecessary sensitive account snapshots are stored in chatbot tables.
- Existing seed data remains the source for account facts and supports every planned supported question.