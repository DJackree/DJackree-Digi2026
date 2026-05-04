# Digicel Assessment — Telecom Customer Portal

## Project overview

This repository is a **Telecom Customer Portal** built for the Digicel take-home assessment. It delivers two main capabilities:

1. **Complaint and fault management** — Customers with linked accounts can **submit complaints**, view **their own** ticket history, and **track status** (they cannot change workflow states). **Agents** see a **queue of complaints assigned to them** (oldest first), can **move status** forward along the defined lifecycle, add **internal notes**, and **escalate** with a reason. **Admins** see **all complaints**, can **assign or reassign agents**, set **any status**, and use a **summary dashboard**: totals **by status** and **by category**, **average resolution time** (from open to resolved), and tickets **past an SLA window** (still open after several days, per implementation). Staff **user and profile maintenance** is done via Django’s built-in **`/admin/`** site; the custom **admin portal** under `/admin-portal/` focuses on complaints and metrics.

2. **AI customer chatbot** — **Logged-in customers** (only) can use a **chat UI** at `/chatbot/` to ask natural-language questions about **their** plan, balance, usage, open complaints, last payment, regional outages, and related topics. Answers are **grounded in database data** passed to the model as context, with prompts that **forbid inventing** account facts. Conversation **history is kept per chat session**.

**Stack:** Python and **Django**, **PostgreSQL**, **Bootstrap** templates, **Docker Compose** for the full stack, and **Groq** (`llama-3.1-8b-instant`) for LLM replies. See [`Documentation/`](Documentation/) for deeper technical notes.

After you configure `.env`, the app is meant to run with **Docker only** — no extra manual migration or seed commands on first boot.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/) (included with Docker Desktop)

## Environment setup

From the [`DigicelAssessment/`](DigicelAssessment/) directory (where `docker-compose.yml` lives):

```bash
cd DigicelAssessment
cp .env.example .env
```

Edit `.env` and set values for your machine. **Do not commit** `.env`; use it locally only.

| Variable | Description |
|----------|-------------|
| `DJANGO_SECRET_KEY` | Secret key for sessions and CSRF. |
| `DJANGO_DEBUG` | Debug flag (e.g. `True` locally). |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts (e.g. `localhost,127.0.0.1`). |
| `POSTGRES_DB` | Database name. |
| `POSTGRES_USER` | Database user. |
| `POSTGRES_PASSWORD` | Database password (must match the Compose `db` service). |
| `POSTGRES_HOST` | Use `db` when the app runs in the `web` container. |
| `POSTGRES_PORT` | Usually `5432`. |
| `GROQ_API_KEY` | Key from [Groq Console](https://console.groq.com) for the chatbot (`llama-3.1-8b-instant`). |
| `GROQ_MODEL` | *(Optional)* Defaults to `llama-3.1-8b-instant`. |
| `GROQ_TIMEOUT_SECONDS` | *(Optional)* Groq request timeout. |
| `CHATBOT_MESSAGE_MAX_LENGTH` | *(Optional)* Max incoming chat message length. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | *(Optional)* Comma-separated origins for CSRF (defaults include `http://localhost:8000`). |
| `GROQ_MAX_COMPLETION_TOKENS` | *(Optional)* Cap on tokens for each Groq completion (default in `settings.py`). |
| `CHATBOT_RECENT_MESSAGE_COUNT` | *(Optional)* How many prior turns are summarized for the model as conversation memory. |
| `CHATBOT_DEFAULT_CURRENCY` | *(Optional)* Currency label shown in chat prompts (default `JMD`). |

For **Groq setup and behaviour** (required key, URLs, defaults), see **Chatbot setup** below.

## Run with Docker

Still in `DigicelAssessment/`:

**First run** (or after changing the image or Dockerfile):

```bash
docker compose up --build
```

**Later runs:**

```bash
docker compose up
```

The `web` service waits for PostgreSQL, runs migrations, seeds the database when it is empty, then serves the app at **http://localhost:8000**.

## Seeding

On first startup, if the database has no users yet, `seed_data --if-empty` runs automatically inside the container. Reviewers do not run a separate seed command. If users already exist, seeding is skipped (reset the DB volume if you need a full re-seed).

## Default login credentials (seeded)

Passwords are set in [`DigicelAssessment/core/management/commands/seed_data.py`](DigicelAssessment/core/management/commands/seed_data.py) for demo only.

| Role | Username | Password |
|------|----------|----------|
| **Admin** | `admin` | `AdminPass123!` |
| **Agent** | `agent1` | `AgentPass123!` |
| **Agent** | `agent2` | `AgentPass123!` |
| **Agent** | `agent3` | `AgentPass123!` |
| **Customer** | `customer1` | `CustomerPass123!` |
| **Customer** | `customer2` | `CustomerPass123!` |
| **Customer** | `customer3` | `CustomerPass123!` |
| **Customer** | `customer4` | `CustomerPass123!` |
| **Customer** | `customer5` | `CustomerPass123!` |

## Chatbot setup

The chatbot uses the **Groq API** and the **`llama-3.1-8b-instant`** model by default (assessment requirement). The `groq` Python package is already listed in [`DigicelAssessment/requirements.txt`](DigicelAssessment/requirements.txt) and is installed when the Docker image builds.

### 1. Get an API key

Create a free key at [Groq Console](https://console.groq.com) (no credit card on the free tier).

### 2. Configure the environment

In [`DigicelAssessment/.env`](DigicelAssessment/.env) (created from [`.env.example`](DigicelAssessment/.env.example)):

- Set **`GROQ_API_KEY`** to your key. **Do not commit** this file; submit real values only in the separate `env_config.txt` (or equivalent) per assessment instructions.

### 3. Optional tuning (same `.env`)

These have defaults in Django settings; override only if needed:

| Variable | Purpose |
|----------|---------|
| `GROQ_MODEL` | Model id (default `llama-3.1-8b-instant`). |
| `GROQ_TIMEOUT_SECONDS` | Request timeout to Groq. |
| `GROQ_MAX_COMPLETION_TOKENS` | Upper bound on completion length. |
| `CHATBOT_MESSAGE_MAX_LENGTH` | Max length for a single user message in the UI/API. |
| `CHATBOT_RECENT_MESSAGE_COUNT` | How many recent messages feed into the prompt as transcript context. |
| `CHATBOT_DEFAULT_CURRENCY` | Currency code in prompts (e.g. `JMD`). |

### 4. Run the application

Start the stack as in **Run with Docker** (for example `docker compose up --build` from `DigicelAssessment/`). No separate “chatbot service” container is required — the `web` process calls Groq when customers send messages.

### 5. Use the chatbot in the UI

1. Sign in as a **customer** (for example `customer1` — see **Default login credentials**).
2. Open **http://localhost:8000/chatbot/** (or use the Chat link from the customer home navigation).
3. Ask account-related questions; replies use **your** seeded `CustomerAccount` data and related records.

Agents and admins **do not** have access to this chat UI by design.

### 6. If the API key is missing

If `GROQ_API_KEY` is empty, the app still loads, but the assistant returns a **clear configuration message** instead of calling Groq. Set the key to exercise full LLM behaviour.

### 7. Automated tests

The test suite **does not require** a live Groq key for most cases; tests **mock** the client where appropriate. Running tests locally still needs PostgreSQL per [`Documentation/commands.md`](Documentation/commands.md).

## Assumptions and design decisions

These are the main choices where the brief allowed interpretation or where implementation detail was left open.

- **User management for admins.** The assessment calls for admins who can “manage users.” That is implemented with Django’s built-in **`/admin/`** interface for `User`, `UserProfile`, and related models. The custom **admin portal** (`/admin-portal/`) focuses on complaints, assignment, and the metrics dashboard—not a second user-CRUD UI.

- **SLA breach rule.** The spec suggests treating tickets still open after about **five days** as breaching SLA. That threshold is implemented in code for the dashboard and filters; it is a simple calendar rule, not business-hours logic.

- **First-run seeding.** `seed_data --if-empty` runs on container startup. If **any** user already exists, seeding is skipped so repeat `docker compose up` does not duplicate demo data. A full re-seed requires clearing the database volume (or an empty database).

- **Roles and access.** Each login maps to one **`UserProfile` role** (customer, agent, admin). Views use decorators to enforce which URLs each role may hit. Customers never receive complaint workflow actions—only read their own tickets and status.

- **Complaint workflow.** Agents may move tickets only **forward** along the defined path and only on **assigned** tickets. Admins may set **any** status and assign agents, matching the separation described in the brief.

- **Chatbot grounding.** Questions are mapped to **intents** with rule-based detection; only the database slices needed for those intents are serialized into **context JSON** passed to Groq, with a system prompt that answers **only** from that context and uses a fixed phrase when data is missing. Some plan-pricing comparisons use **deterministic** answers from precomputed context to avoid arithmetic mistakes by the model.

- **Demo credentials.** Seeded passwords are **deterministic strings** in `seed_data.py` for reviewers only, not a production security pattern.

- **Stack scope.** The front end is **Django templates and Bootstrap** (no React), which satisfies the “and/or React” requirement. The app is intended for **local/demo** use: `DEBUG` defaults friendly for development; production hardening is out of scope.

## AI usage workflow

Given the number of requirements in the project brief and the short delivery timeframe, I worked with the assumption that AI usage was encouraged because the project description explicitly asked for transparency around AI-assisted work. Based on that assumption, I used AI heavily to help turn my implementation ideas into a complete working assessment while still reviewing, adjusting, and debugging the output myself.

The workflow I used was:

1. I started with a detailed markdown file containing all project requirements. This was based on the provided project description: [`Overview and Plans/Project Overview/ProjectDescription.md`](Overview%20and%20Plans/Project%20Overview/ProjectDescription.md).
2. Using that requirements document, I broke the project into three main modules: Auth, Complaints, and Chatbot. I then used a high-reasoning AI model (GPT) to break each module into implementation phases:
   - Database setup
   - API setup
   - UI setup
3. I reviewed those plans manually and adjusted them where needed.
4. Once the plans covered the requirements, I used a high-reasoning model (GPT) to build detailed implementation plans for each module phase. For example, GPT was used to create `.cursor/plans/phase_1_foundation_e36ba880.plan.md`. I reviewed each implementation plan, adjusted it when I found gaps, then used a faster implementation model (Composer) to execute the plan.
5. After each implementation pass, I reviewed, adjusted, and debugged the generated code.
6. When I ran into architectural issues or larger design concerns, I created a new markdown prompt to guide a refactor, then repeated the implementation-plan workflow from step 4 without splitting the work into smaller phases.

Steps 4, 5, and 6 were repeated until the project was complete.

### AI planning artifacts

- [`Overview and Plans/Prompts/0-InitalPrompt.md`](Overview%20and%20Plans/Prompts/0-InitalPrompt.md) was used to create the plans in `Overview and Plans/Plans` (step 2 of the workflow).
- [`Overview and Plans/Prompts/1-RefactorPlansStructure.md`](Overview%20and%20Plans/Prompts/1-RefactorPlansStructure.md) was used to refactor the plans after the first draft was not in the format I wanted.
- [`Overview and Plans/Prompts/2-ChatbotRefactor.md`](Overview%20and%20Plans/Prompts/2-ChatbotRefactor.md) was used to refactor the chatbot to account for additional scenarios (step 6 of the workflow).
- `Overview and Plans/Chats` contains transcripts of the core Cursor chats. Chat `00` was used to build the plans in `Overview and Plans/Plans`, and chats `01` through `03` were used to implement the modules in phases. Additional chats were used during development, but these are the main ones relevant to the final project.
- `.cursor/plans` contains the implementation plans generated with the high-reasoning model (GPT) before implementation.
