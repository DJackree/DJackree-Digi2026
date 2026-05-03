# Module preparation document review
_Exported on 5/2/2026 at 21:15:59 AST from Cursor (3.2.16)_

---

**User**

Consume @Overview and Plans/Chats/cursor_00_implementation_plans_based_on_pr.md @Overview and Plans/Chats/cursor_01_system_architchture.md @Overview and Plans/Chats/cursor_02_complaint_and_fault.md to see what was done so far in Preparation for the next module 

---

**Cursor**

Reading the three chat/overview files to summarize progress and context for the next module.



Here is a condensed picture from those three exports, oriented toward **what is done** and **what comes next**.

## Planning groundwork (`cursor_00`)

- **`InitialPrompt`** + **`ProjectDescription`** drove a **`Plans`** set: master + architecture + complaint + chatbot (+ delivery/seed docs).
- **`1-RefactorPlansStructure`** refactored so:
  - **`01`** = project / DB / auth / shared foundation  
  - **`02`** = complaint & fault management  
  - **`03`** = AI customer chatbot  
  - Cross-cutting items went into **`00-master-implementation-plan.md`**; old `04`/`05` were removed after merge.
- Every numbered plan uses **Phase 1 — DB**, **Phase 2 — API/backend**, **Phase 3 — UI**.

## System architecture — fully implemented (`cursor_01`)

All three phases of **`01-system-architecture-plan`** were implemented under **`DigicelAssessment/`**:

| Phase | What landed |
|--------|-------------|
| **1 — DB** | Django project/apps (`config`, `accounts`, `customers`, `core`), `UserProfile` + customer models, migrations, admin, Postgres + env/dotenv, `seed_data --if-empty`, README/deps (`groq` reserved for later). |
| **2 — API** | Dockerfile + Compose (db + web), entrypoint (wait → migrate → seed → runserver), login URLs/settings, **`role_required`**-style decorators, role-aware views/URLs, `get_customer_account_for_user`. |
| **3 — UI** | **`base.html`** (Bootstrap 5, messages, role nav), **`safe_user_profile`**, **`BootstrapAuthenticationForm`**, role landing pages, **`MESSAGE_TAGS`** for Bootstrap. |

## Complaint & fault module — fully implemented (`cursor_02`)

All three phases of **`02-complaint-and-fault-management-plan`** are done:

| Phase | What landed |
|--------|-------------|
| **1 — DB** | Apps **`complaints`**, **`network`**, **`dashboard`**; **`Complaint`**, notes, status history (reference **`CMP-YYYY-NNNN`**), **`NetworkOutage`**; migrations, admin; seed extended (complaints, histories, notes, outages, SLA breach samples). Index rename migration on **`AccountUsage`** noted in the chat. |
| **2 — Backend** | Forms, **`complaints/services.py`** (transitions, status changes, assignment, escalation, SLA helpers), role-scoped views/URLs, **`dashboard/services.get_dashboard_metrics`**, navbar wiring, minimal-but-usable templates, **`complaints`** + **`dashboard`** tests (full test runs were **aborted** in-agent when Postgres/test DB stalled; rerun locally with DB up). |
| **3 — UI** | Template tags for labels/badges, customer timeline **without** internal note text, agent/admin **GET filters** (status, category, agent, SLA breach), dashboard status cards / category breakdown / SLA table with ages, README + landing-page links into complaints/dashboard. **`manage.py check`** / **`compileall`** reported OK in that session; full **`manage.py test`** again recommended locally. |

---

## Preparation for the **next module**

Per the agreed plan ladder, **`Overview and Plans/Plans/03-ai-customer-chatbot-plan.md`** is next: deterministic Groq-based chatbot on top of the existing **customers + complaints + roles + Bootstrap shell**, still following **Phase 1 — DB**, **Phase 2 — Backend**, **Phase 3 — UI** as written there.

Before or while starting **`03`**, it is worth **running tests locally** with Postgres available (`manage.py test complaints dashboard` — and any app you add for the chatbot) so you are not blocked by the same test-DB/connectivity limits the agent hit.

---

**User**

Build a plan to Implement Phase 1 of @Overview and Plans/Plans/03-ai-customer-chatbot-plan.md 

---

**Cursor**

I’ll read the chatbot plan and the current Django app structure so the Phase 1 plan fits the existing DB, seed, admin, and app patterns without drifting into backend/UI work.

Phase 1 is clearly limited to persistence: create/register the `chatbot` app, add session/message models and admin, and verify existing seed dependencies rather than adding Groq calls or chat routes yet. I’m checking whether any chatbot files already exist and the nearby admin conventions before finalizing the plan.

The current repo has no `chatbot` app yet, and the existing seed data already contains the account, usage, payment, complaints, and outage records Phase 1 needs. I’ll turn this into a focused DB/admin/verification plan only, leaving intent detection, Groq, routes, and UI for later phases.

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

Implementing Chatbot Phase 1: marking the first todo in progress and scaffolding the chatbot app.



Creating the chatbot app structure and registering it in settings.



Simplifying the session index to `["user", "updated_at"]` for broad Django compatibility and adding a manual migration after `makemigrations` hung.



Adding Role choices to the migration to match the model and writing `tests.py`.



Here's what was implemented for **Chatbot Phase 1**:

### New `chatbot` app (`DigicelAssessment/chatbot/`)
- **`apps.py`** – `ChatbotConfig` with `verbose_name = "AI Chatbot"`.
- **`models.py`** – `ChatSession` (FK to `User`, `title`, timestamps, `ordering = -updated_at`) and `ChatMessage` (`Role` user/assistant, `content`, `intent`, FK to session, `ordering = created_at`). Indexes: `(user, updated_at)` on sessions, `(session, created_at)` on messages (`user` / `updated_at` index matches the intent of the plan without relying on a descending fragment in the index tuple for older Django edge cases).

### Django wiring
- **[`DigicelAssessment/config/settings.py`](DigicelAssessment/config/settings.py)** – `"chatbot"` added to `INSTALLED_APPS`.

### Admin
- **`admin.py`** – `ChatSessionAdmin` / `ChatMessageAdmin` with list display, filters, search, autocomplete (`user`, `session`), date hierarchy, read-only timestamps.

### Migrations
- **`chatbot/migrations/0001_initial.py`** – creates both models and indexes (role choices embedded in migration).

### Tests & docs
- **`chatbot/tests.py`** – ordering, cascade delete on session, isolation per user, `full_clean()` rejection of invalid roles.
- **[`DigicelAssessment/README.md`](DigicelAssessment/README.md)** – Phase 1 section: persistence only, no transcript seeding, Groq/key only in Phase 2+, intent coverage tied to **`seed_data` on an empty DB**, and how to run `python manage.py test chatbot`.

### Verification run here
- `python manage.py check` → **0 issues**.
- `python -m compileall chatbot` → OK.  
`migrate` / full `test chatbot` need Postgres up (commands were likely waiting on DB in this environment). On your machine, from `DigicelAssessment/`:

```bash
python manage.py migrate
python manage.py test chatbot
```

All related plan to-dos are **completed**. The plan markdown file itself was **not** edited.

---

**User**

<system_notification>
The following task has finished. If you were already aware, ignore this notification and do not restate prior responses.

<task>
kind: shell
status: success
task_id: 898822
title: Generate chatbot initial migration with Django
output_path: C:\Users\Djackree\.cursor\projects\c-Users-Djackree-Desktop-Repos-DigicelAssessment\terminals\898822.txt
</task>
</system_notification>
<user_query>Briefly inform the user about the task result and perform any follow-up actions (if needed).</user_query>

---

**Cursor**

Checking the migration task output for conflicts with our manually added migration.



Noting `makemigrations` succeeded (exit 0) but emitted a DB connection warning. The generated migration uses `user`, `-updated_at` while `models.py` still uses `user`, `updated_at` — aligning the model with the migration so `makemigrations` won't create a spurious follow-up.



**Task result:** `python manage.py makemigrations chatbot --name initial` **finished successfully** (exit code **0**) and regenerated [`chatbot/migrations/0001_initial.py`](DigicelAssessment/chatbot/migrations/0001_initial.py) using **Django 5.2.13**. Postgres wasn’t reachable on `localhost:5432`, so Django showed a **RuntimeWarning** about checking migration history on the database—**it doesn’t block writing migration files**.

**Follow-up:** The generated migration uses an index on **`user` + `-updated_at`**. `ChatSession` in [`chatbot/models.py`](DigicelAssessment/chatbot/models.py) was updated to use the **same** `Index(fields=["user", "-updated_at"], …)` so the models and **`0001_initial`** stay consistent and **`makemigrations` won’t** try to alter that index later.

**What you should do locally:** Bring Postgres up (per your `.env`), then run `python manage.py migrate` so the chatbot tables apply.

---

**User**

<system_notification>
The following task has finished. If you were already aware, ignore this notification and do not restate prior responses.

<task>
kind: shell
status: error
task_id: 905468
title: Try migrate chatbot with dummy Postgres config (may fail if no DB)
detail: exit_code=1
output_path: C:\Users\Djackree\.cursor\projects\c-Users-Djackree-Desktop-Repos-DigicelAssessment\terminals\905468.txt
</task>
</system_notification>
<user_query>Briefly inform the user about the task result and perform any follow-up actions (if needed).</user_query>

---

**Cursor**

**Task result:** The `migrate chatbot` run **failed** (exit **1**) with **`OperationalError` / connection timeout**: nothing was answering PostgreSQL on **`localhost:5432`** (`::1` and `127.0.0.1`).

**Cause:** Postgres wasn’t running (or firewall/host/port didn’t match), and the dummy `POSTGRES_*` values weren’t validated because the TCP connection never succeeded.

**What to do:** Start your DB (`docker compose up -d db` or full stack), ensure `.env` has the right **`POSTGRES_HOST`** (e.g. `localhost` when Django runs on the host, `db` in the **web** container), then rerun:

```bash
cd DigicelAssessment
python manage.py migrate chatbot --noinput
```

No repo/code follow-up required for this failure.

---

**User**

<system_notification>
The following task has finished. If you were already aware, ignore this notification and do not restate prior responses.

<task>
kind: shell
status: error
task_id: 213984
title: Apply chatbot migrations against configured Postgres
detail: exit_code=1
output_path: C:\Users\Djackree\.cursor\projects\c-Users-Djackree-Desktop-Repos-DigicelAssessment\terminals\213984.txt
</task>
</system_notification>
<user_query>Briefly inform the user about the task result and perform any follow-up actions (if needed).</user_query>

---

**Cursor**

**Task result:** Applying chatbot migrations **failed** (exit **1**) with **`OperationalError`** / **`psycopg.errors.ConnectionTimeout`**: Django could not reach PostgreSQL at **`localhost:5432`** (both IPv6 and IPv4 timed out).

**Why:** Postgres wasn’t available from that environment (Compose DB not running, wrong `POSTGRES_HOST`/port for how you’re running Django, etc.)—not an application migration bug.

**Next step:** Start Postgres (`docker compose up -d db` or `docker compose up --build`), align `.env` (`POSTGRES_HOST=localhost` when using host-run Django vs `db` inside the web container), then rerun `python manage.py migrate chatbot` (or `migrate`).

**Follow-up:** None required in the codebase for this outcome.

---

**User**

<system_notification>
The following task has finished. If you were already aware, ignore this notification and do not restate prior responses.

<task>
kind: shell
status: error
task_id: 277223
title: Emit SQL for chatbot 0001 without DB connection requirement
detail: exit_code=1
output_path: C:\Users\Djackree\.cursor\projects\c-Users-Djackree-Desktop-Repos-DigicelAssessment\terminals\277223.txt
</task>
</system_notification>
<user_query>Briefly inform the user about the task result and perform any follow-up actions (if needed).</user_query>

---

**Cursor**

**Task result:** The `sqlmigrate chatbot 0001` command **failed** (exit **1**) with the same issue as `migrate`: **`ConnectionTimeout`** to PostgreSQL on **`localhost:5432`**.

**Why the assumption was wrong:** With the **PostgreSQL** backend, Django’s `sqlmigrate` still **opens a database connection** (schema/SQL generation path), so it won’t work if Postgres isn’t up/reachable.

**Follow-up:** Start Postgres (or fix `POSTGRES_HOST`/port in `.env`), then rerun:

```bash
python manage.py sqlmigrate chatbot 0001
```

No repository changes are required for this failure.

---

**User**

<system_notification>
The following task has finished. If you were already aware, ignore this notification and do not restate prior responses.

<task>
kind: shell
status: error
task_id: 412168
title: Verify no pending chatbot migrations after model alignment
detail: exit_code=1
output_path: C:\Users\Djackree\.cursor\projects\c-Users-Djackree-Desktop-Repos-DigicelAssessment\terminals\412168.txt
</task>
</system_notification>
<user_query>Briefly inform the user about the task result and perform any follow-up actions (if needed).</user_query>

---

**Cursor**

Investigating migration drift: `makemigrations --check` failed because Meta options (`verbose_name`) differ from `0001_initial`. Fixing `0001_initial.py` so it matches the models and no pending migration remains.



**Task result:** `makemigrations chatbot --check --dry-run` exited **1** because Django **wanted a new migration** (`0002_...`) updating **`verbose_name` / `verbose_name_plural`** on `ChatSession` and `ChatMessage`—those **`Meta`** options existed in **`models.py`** but **not** in **[`chatbot/migrations/0001_initial.py`](DigicelAssessment/chatbot/migrations/0001_initial.py)**.

There was also the usual **`RuntimeWarning`** about Postgres migration-history checks **`connection timeout`** (DB not up); that warning alone doesn’t always fail the command, but **`--check` fails whenever any model changes remain**.

**Follow-up (done):** **`0001_initial.py`** was updated so both `CreateModel` `options` blocks include the same **`verbose_name`** values as `models.py`. Re-running **`makemigrations chatbot --check --dry-run`** now reports **no changes** (exit **0**).

**If you’d already applied the old `0001`** on another machine DB: don’t edit `0001` in place—add a **`0002_alter_*_options`** migration instead.

---

**User**

Build a plan to Implement Phase 2 of @Overview and Plans/Plans/03-ai-customer-chatbot-plan.md 

---

**Cursor**

I’ll review the Phase 2 chatbot requirements plus the existing auth, data, and complaint services so the backend plan fits the current Django patterns and keeps the LLM constrained to customer-scoped context.

The plan needs Phase 2 to add backend modules around the Phase 1 `ChatSession`/`ChatMessage` models, plus a `GROQ_API_KEY` setting that the current settings file does not yet expose. I’m checking view/test conventions and Groq SDK docs shape before finalizing.

I have enough context now: Phase 2 should be a backend slice with deterministic intent detection, scoped context builders, Groq wrapper/error handling, customer-only views/URLs, persistence, and tests. I’ll create the plan around existing `role_required`, `get_customer_account_for_user`, and the Phase 1 chat models.

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

Implementing Chatbot Phase 2: starting with settings and URL routing, then adding intent/context/prompt/Groq layers, views, template, nav, tests, and README updates.



Adding settings and URL routing, then implementing intents, context, prompts, groq_client, views, template, nav, tests, and README.



Fixing the Groq error handling and implementing `views.py`, `urls.py`, template, and nav updates.



Implementing streamlined `views.py` and fixing duplicate exception handling.



Fixing a false-positive: normalized text like `"neighbor s balance"` can match `\bbalance\b`. Adding an early unsupported guard for third-party references (neighbor/cousin, etc.), then updating the README and running tests.



### Done (Chatbot Phase 2)

**Settings / routing**

- **[`DigicelAssessment/config/settings.py`](DigicelAssessment/config/settings.py)** — `GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_TIMEOUT_SECONDS`, `GROQ_MAX_COMPLETION_TOKENS`, `CHATBOT_MESSAGE_MAX_LENGTH`, `CHATBOT_RECENT_MESSAGE_COUNT`, `CHATBOT_DEFAULT_CURRENCY`.
- **[`DigicelAssessment/config/urls.py`](DigicelAssessment/config/urls.py)** — includes **`chatbot.urls`**.
- **[`DigicelAssessment/chatbot/urls.py`](DigicelAssessment/chatbot/urls.py)** — `GET /chatbot/`, `POST /chatbot/messages/`, `POST /chatbot/sessions/new/`.

**Deterministic backend**

- **[`DigicelAssessment/chatbot/intents.py`](DigicelAssessment/chatbot/intents.py)** — keyword intents + guard for third‑party wording (neighbor/cousin/etc. → **`unsupported`** to avoid bogus “balance” hits).
- **[`DigicelAssessment/chatbot/context.py`](DigicelAssessment/chatbot/context.py)** — customer‑scoped contexts (plan, balance, usage, open complaints excluding internal notes/description, last payment, active outages by **account region case‑insensitive**).
- **[`DigicelAssessment/chatbot/prompts.py`](DigicelAssessment/chatbot/prompts.py)** — strict system/user prompts + bounded recent transcript serialization.
- **[`DigicelAssessment/chatbot/groq_client.py`](DigicelAssessment/chatbot/groq_client.py)** — `Groq` client w/ timeout, `temperature=0.1`, Groq **`APIConnectionError` / `APIStatusError`** mapped to **`ChatbotGroqTransientError`**.
- **[`DigicelAssessment/chatbot/views.py`](DigicelAssessment/chatbot/views.py)** — `@role_required(CUSTOMER)` only, JSON API w/ persistence, **`unsupported` skips Groq**, missing key friendly reply, transient errors surfaced safely, **`404`** for another user’s **session**.
- **[`DigicelAssessment/templates/chatbot/chat.html`](DigicelAssessment/templates/chatbot/chat.html)** — minimal transcript + **`fetch`** JSON posts w/ **`X-CSRFToken`**.
- **[`DigicelAssessment/templates/base.html`](DigicelAssessment/templates/base.html)** — real **Chatbot** nav link for customers.

**Docs / env**

- **[`DigicelAssessment/README.md`](DigicelAssessment/README.md)** — Phase 2 routes, CSRF, env knobs.
- **[`DigicelAssessment/.env.example`](DigicelAssessment/.env.example)** — optional Groq‑related overrides.

**Tests**

- **[`DigicelAssessment/chatbot/tests.py`](DigicelAssessment/chatbot/tests.py)** — intent samples, complaint isolation/context shape, Groq mocking, access control, missing key path, transient errors.

**Verification**

- `python manage.py check` ✅ (0 issues).
- `python manage.py test chatbot` was **started** but looked **stuck creating the Postgres test DB** here (slow/unreachable Postgres). Please rerun locally when Docker/DB is up; code **byte‑compiles** (`python -m compileall chatbot` ✅).

Plan file unchanged. All Phase 2 plan to‑dos marked **completed**.

---

**User**

<system_notification>
The following task has finished. If you were already aware, ignore this notification and do not restate prior responses.

<task>
kind: shell
status: error
task_id: 52301
title: Run chatbot tests after fixing import syntax
detail: exit_code=1
output_path: C:\Users\Djackree\.cursor\projects\c-Users-Djackree-Desktop-Repos-DigicelAssessment\terminals\52301.txt
</task>
</system_notification>
<user_query>Briefly inform the user about the task result and perform any follow-up actions (if needed).</user_query>

---

**Cursor**

**Task result:** `python manage.py test chatbot -v 2` **failed** (exit **1**) while **creating the Postgres test DB** (`test_telecom_portal`). Django found **17** tests, then raised **`OperationalError` / connection timeout** to **`localhost:5432`** (IPv4 and IPv6), so **no tests actually ran**.

**Cause:** Postgres wasn’t reachable from the host environment (Compose DB stopped, firewall, or `.env` `POSTGRES_HOST`/port not matching how you’re running Django).

**What to do:** Start Postgres (`docker compose up -d db` or full stack), set **`POSTGRES_HOST=localhost`** in `.env` when running Django on Windows (not `db`), then rerun:

```bash
cd DigicelAssessment
python manage.py test chatbot -v 2
```

**Follow-up in the repo:** None required—the failure was environmental, not import/test logic.

---

**User**

add this command to @Documentation/commands.md with relevant documentation on what the workflow does 

---

**Cursor**

Adding a "Django automated tests" section documenting the chatbot test command and the test-database workflow.



Added a new **[`Documentation/commands.md`](Documentation/commands.md)** section, **“Django: automated tests (`chatbot` app)”**, which documents:

- **`python manage.py test chatbot -v 2`** (run from **`DigicelAssessment/`**, venv on, Postgres up)
- **What the workflow does**: connect with `.env` → create **`test_…`** DB → migrate → run **`chatbot.tests`**
- **Prerequisites / failure meaning** (Postgres reachability, `POSTGRES_HOST=localhost` on the host)
- **`--keepdb`** for faster reruns
- **`python manage.py test complaints dashboard chatbot -v 2`** for a broader suite

The existing **“Django: checks”** block is unchanged and still follows that section.

---

**User**

Build a plan to Implement Phase 3 of @Overview and Plans/Plans/03-ai-customer-chatbot-plan.md 

---

**Cursor**

I’ll review the Phase 3 chatbot UI requirements and the current Phase 2 backend/template so the plan focuses on UI polish without reworking the backend.

The backend routes and customer nav already exist, and the current chat template is a minimal Phase 2 implementation with inline fetch. The Phase 3 plan will focus on replacing that with a polished Bootstrap chat experience, adding suggested questions, better loading/error states, transcript behavior, and UI-oriented tests/docs.

---

**User**

Implement the plan as specified, it is attached for your reference. Do NOT edit the plan file itself.

To-do's from the plan have already been created. Do not create them again. Mark them as in_progress as you work, starting with the first one. Don't stop until you have completed all the to-dos.

---

**Cursor**

Implementing Chatbot Phase 3: starting layout polish and working through todos.



Implementing polished layout, `static/chatbot.js`, and fixing new-session routing: `/chatbot/` currently picks the most recently updated session, so a freshly created empty session can lose to an older chat — we'll honor `?session=<id>` in `chat_home`.



Implementing views session resolution, `chatbot/static/chatbot/chatbot.js`, redesigned `chat.html`, tests, and README updates.



Moving textarea clearing to after a successful POST per the plan, then adding Phase 3 tests and README updates.



Here’s what was finished for **Phase 3** from the summarized work plus this round:

### Done
1. **`chatbot.js`** – Thinking bubble width kept as inline style; user bubble label uses `text-white-50` instead of invalid `opacity-85`. Textarea is **cleared only after a successful** assistant reply (per plan); failures keep the draft so the user can retry.
2. **`chat.html`** – Empty state heading uses **Hello** instead of the emoji.
3. **`chatbot/tests.py`** – **`ChatbotPhase3UITests`**: suggests `CHATBOT_SUGGESTED_QUESTIONS`, CSRF, static `/chatbot/chatbot.js`, transcript id; chronological transcript in HTML; **`?session=`** loads the empty session over the default “latest”; customer nav includes chat URL; agent & admin landing pages **omit** chat URL; customer with **no linked account** sees the warning copy. Import: `from chatbot.views import CHATBOT_SUGGESTED_QUESTIONS`.
4. **`README.md`** – Phase 3 UI bullets, **`?session=`** note on `GET /chatbot/`, `python manage.py check` + **`test chatbot -v 2`**, and manual QA steps aligned with the plan.
5. **Todos** – All six items marked **completed**.

### Verification on your machine
- `python manage.py check` succeeded here.
- `python manage.py test chatbot` **started creating the Postgres test DB** then appeared to **block** without a reachable DB (nothing wrong with the test code—Postgres/env must be up).

Run locally (with Postgres as in README):

```bash
cd DigicelAssessment && python manage.py check && python manage.py test chatbot -v 2
```

Phase 2 endpoints and customer-only access are unchanged; nav is still **`Chatbot` for customers only** in `templates/base.html`, with tests covering customer vs agent/admin.

---

**User**

<system_notification>
The following task has finished. If you were already aware, ignore this notification and do not restate prior responses.

<task>
kind: shell
status: error
task_id: 879343
title: Run Django check and chatbot test suite
detail: exit_code=1
output_path: C:\Users\Djackree\.cursor\projects\c-Users-Djackree-Desktop-Repos-DigicelAssessment\terminals\879343.txt
</task>
</system_notification>
<user_query>Briefly inform the user about the task result and perform any follow-up actions (if needed).</user_query>

---

**Cursor**

Summarizing: `manage.py check` passed; `manage.py test chatbot` ran 24 tests — 21 passed; 3 failed (2 assertion failures using `html=True`, 1 `IntegrityError`: assistant message had `intent=None` — DB rejects NULL). Fixing the tests now.



### Earlier run (task **879343**)
- **`python manage.py check`** succeeded.
- **`python manage.py test chatbot`** exited **1**: **21 passed**, **2 failed**, **1 error**.
  - **`assertContains(..., html=True)`** couldn’t match substrings like `id="chatTranscript"` / `href="/chatbot/"` even though those strings appeared in the raw HTML.
  - **`test_transcript_round_trips_ordered_in_markup`** tried to insert an assistant row with **`intent=None`**, but **`intent`** is **NOT NULL** in the DB (`CharField(blank=True)` still stores `''`, not SQL `NULL`).

### Follow-up (done)
- Updated **`chatbot/tests.py`**: substring checks **without** `html=True`; assistant fixture uses a non-null **`intent`** (e.g. `"current_plan"`).
- Re-ran **`python manage.py test chatbot -v 2`** — **24/24 OK** (~72s).

You may still see Django’s Postgres **`RuntimeWarning`** about connecting to `postgres`; it doesn’t fail the suite.

