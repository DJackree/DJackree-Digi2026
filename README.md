# Digicel Assessment — Telecom Customer Portal

Django app with PostgreSQL and a Groq-backed customer chatbot. Run everything with Docker Compose (no extra manual steps after `.env` is configured).

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

**Chatbot:** the app expects a valid `GROQ_API_KEY` in `.env` for full chatbot behaviour. Optional variables above can be omitted unless you need to override defaults.

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
