# Technical Interview Study Plan

One-day preparation plan for the **Digicel Software Development & Design Engineer** technical interview, using:

- Job description: `Overview and Plans/Job Description/JD.md`
- Resume: `Overview and Plans/Job Description/Copy of Dinesh Jackree.pdf`
- Project brief: `Overview and Plans/Project Overview/ProjectDescription.md`
- Submitted project: Telecom Customer Portal in this repository

## Interview Goal

Your goal is to show that you can:

- Translate broad business requirements into a working technical solution.
- Explain architecture decisions, trade-offs, and implementation details clearly.
- Own a system end-to-end: requirements, design, development, testing, deployment, documentation, and support.
- Connect your project decisions to Digicel's telecom environment: reliability, supportability, customer impact, observability, and maintainability.
- Speak honestly about AI usage while proving that you understand and can defend the code.

## One-Day Schedule

### Hour 1: Role and Resume Alignment

Focus: connect your background to the job description.

Review:

- JD duties: SDLC execution, architecture, documentation, legacy stabilisation, testing, support, automation, stakeholder communication.
- Resume themes:
  - Tier 2/3 production support at Stavvy.
  - Performance and latency improvement.
  - Technical documentation and API/integration docs.
  - CI/CD pipeline design.
  - Docker/self-hosting experience.
  - HRplus modernization, reporting/BI work, ISO 27001 documentation.
  - Met Office internal systems and training.

Prepare a 90-second intro:

```text
I am a software developer with experience across full-stack development, production support, documentation, integrations, and system modernization. My recent work includes supporting fintech web applications, troubleshooting production issues, improving performance, and documenting APIs and architecture. For this Digicel assessment, I built a Django/PostgreSQL telecom portal with complaint management, role-based workflows, Docker deployment, seeded demo data, and a Groq-backed chatbot that answers from database context. The project lines up well with this role because it combines solution design, maintainability, testing, support workflows, and clear documentation.
```

### Hour 2: Project Walkthrough

Focus: be able to explain the app from top to bottom.

Practice this flow:

1. **Problem statement**
   - Build a telecom customer portal with complaint/fault management and a grounded AI chatbot.

2. **Architecture**
   - Django project with local apps:
     - `accounts`: roles, login routing, decorators.
     - `customers`: service plans, customer accounts, usage, payments.
     - `complaints`: ticket model, workflow, notes, assignment, escalation.
     - `dashboard`: admin metrics.
     - `network`: outage records.
     - `chatbot`: sessions, messages, intents, context, Groq.
     - `core`: seed command.

3. **Runtime**
   - Docker Compose starts PostgreSQL and web.
   - `entrypoint.sh` waits for Postgres, runs migrations, seeds if empty, and starts Django.

4. **Data model**
   - User + UserProfile for roles.
   - CustomerAccount linked to ServicePlan, usage, payments.
   - Complaint linked to account and assigned agent.
   - ComplaintNote and ComplaintStatusHistory for staff notes and audit trail.
   - NetworkOutage for regional fault context.
   - ChatSession and ChatMessage for conversation persistence.

5. **Main workflows**
   - Customer: log in, submit complaint, view own complaints, use chatbot.
   - Agent: see assigned queue, update status forward, add notes, escalate.
   - Admin: see all tickets, assign agents, override status, dashboard, manage users through Django admin.

### Hour 3: Complaint System Deep Dive

Focus: show you understand business rules and code boundaries.

Know these files:

- `DigicelAssessment/complaints/models.py`
- `DigicelAssessment/complaints/services.py`
- `DigicelAssessment/complaints/views.py`
- `DigicelAssessment/dashboard/services.py`

Talking points:

- Complaint lifecycle: **Open -> In Progress -> Escalated -> Resolved -> Closed**.
- Agents can only move forward and only on assigned tickets.
- Admins can assign agents and set any status.
- Customers can view status, but cannot change workflow.
- Internal notes are staff-only.
- SLA breach is a simple five-day rule for non-terminal complaints.
- Dashboard uses query-based metrics:
  - total by status,
  - total by category,
  - average resolution time,
  - SLA breach list.

Likely questions:

- **Why use services instead of putting all logic in views?**
  - Services keep business rules reusable and testable. Views validate forms and render templates; services enforce permissions and workflow.

- **How do you prevent agents from changing tickets that are not assigned to them?**
  - `complaints.services._ensure_agent_assigned()` is called before agent status changes, notes, or escalation.

- **How would you improve the SLA logic in production?**
  - Make SLA configurable per category/priority, use business hours, add escalation notifications, and store SLA deadlines explicitly.

### Hour 4: Chatbot Deep Dive

Focus: prove the chatbot is grounded and privacy-conscious.

Know these files:

- `DigicelAssessment/chatbot/intents.py`
- `DigicelAssessment/chatbot/context.py`
- `DigicelAssessment/chatbot/prompts.py`
- `DigicelAssessment/chatbot/groq_client.py`
- `DigicelAssessment/chatbot/views.py`
- `DigicelAssessment/chatbot/models.py`

Explain the pipeline:

1. Customer sends message from `/chatbot/`.
2. View validates session ownership and message length.
3. `detect_intents()` maps the question to supported topics.
4. `build_merged_chat_context()` fetches only the required database facts.
5. Prompt tells Groq to answer only from `ACCOUNT_CONTEXT`.
6. User and assistant messages are stored in `ChatMessage`.
7. Recent transcript supports follow-up questions.

Key examples:

- "What plan am I on?" -> current plan context.
- "What is my balance?" -> account balance context.
- "How much data have I used?" -> usage + plan allowance context.
- "Do I have open complaints?" -> customer's non-terminal complaints.
- "When was my last payment?" -> latest payment.
- "Are there outages in my area?" -> active outages for customer's region.

Likely questions:

- **How do you reduce hallucination?**
  - Use intent-based context, strict system prompt, missing-info phrase, and no broad database dump.

- **Why rule-based intents instead of an LLM deciding everything?**
  - Predictable, testable, lower cost, easier to reason about for assessment scope. It also protects privacy by controlling which context is fetched.

- **How is conversation history handled?**
  - `ChatSession` groups messages, `ChatMessage` stores each turn, and a limited recent transcript is sent for conversational continuity.

- **What happens if Groq is down or the API key is missing?**
  - Missing key returns a clear configuration message; upstream failures return a friendly unavailable message.

### Hour 5: Docker, Environment, and Seeding

Focus: be able to explain first-run behavior confidently.

Know these files:

- `DigicelAssessment/docker-compose.yml`
- `DigicelAssessment/Dockerfile`
- `DigicelAssessment/entrypoint.sh`
- `DigicelAssessment/core/management/commands/seed_data.py`
- `DigicelAssessment/.env.example`

Talking points:

- Compose has `db` and `web`.
- `web` depends on healthy Postgres.
- `POSTGRES_HOST` is overridden to `db` inside Docker.
- `entrypoint.sh` runs:
  - wait for Postgres,
  - migrate,
  - seed if empty,
  - runserver.
- Seed data includes:
  - five customers,
  - three agents,
  - one admin,
  - three plans,
  - account balances and usage,
  - payments,
  - fifteen complaints,
  - two outages.

Likely questions:

- **Why seed only if empty?**
  - Prevents duplicate demo data on repeated Docker starts.

- **What would you change for production?**
  - Use Gunicorn/ASGI server, environment-specific settings, stricter secrets, HTTPS, proper logging, monitoring, migrations through release pipeline, and remove dev `runserver`.

### Hour 6: Testing and Quality

Focus: show the code was not just generated; it was validated.

Review:

- `DigicelAssessment/chatbot/tests.py`
- `DigicelAssessment/complaints/tests.py`
- `DigicelAssessment/dashboard/tests.py`
- README and Documentation updates.

Talking points:

- Tests cover chatbot model/session behavior, access control, JSON API, intents, context isolation, mocked Groq behavior, and UI template expectations.
- Complaint tests cover workflow, permissions, notes, escalation, SLA, and views.
- You used documentation as part of quality, not an afterthought.

Likely questions:

- **What would you test next with more time?**
  - End-to-end browser tests for role workflows, seed command assertions, Docker smoke test in CI, and load testing around complaint queues/chatbot calls.

- **How would you handle performance as data grows?**
  - Keep indexes on status/category/agent/account, add pagination, cache dashboard aggregates if needed, and avoid sending large chatbot contexts.

### Hour 7: Architecture and Trade-Off Questions

Prepare concise answers for these.

#### Why Django?

Django fits the project because it gives auth, ORM, admin, templates, migrations, and security defaults quickly. For an assessment with roles, relational data, and admin workflows, it reduces boilerplate and keeps the design maintainable.

#### Why PostgreSQL?

The data is relational: users, accounts, plans, complaints, payments, usage, and outage records. PostgreSQL supports integrity, indexes, transactions, and reporting queries well.

#### Why Django templates instead of React?

The brief allowed Django templates with Bootstrap and/or React. Templates were faster and appropriate for server-rendered role workflows. It kept the app simpler and let more time go into backend rules, seeding, Docker, and chatbot grounding.

#### Why Django admin for user management?

The assessment required admins to manage users. Django admin already provides a mature, secure CRUD interface for `User` and `UserProfile`. The custom admin portal focuses on telecom-specific operations: complaint assignment, status, and reports.

#### What is the biggest technical risk?

The chatbot is the highest risk because LLMs can hallucinate. The mitigation is strict context construction, explicit prompting, missing-info fallback, deterministic handling for sensitive plan-price comparisons, and storing conversations for auditability.

#### What would you improve with another week?

- Add pagination and search across complaint lists.
- Add formal priority/SLA model.
- Add staff-visible outage management UI.
- Add email/SMS notifications for complaint updates.
- Add CI pipeline with test and Docker build.
- Add structured logs and monitoring.
- Add more browser-level end-to-end tests.

### Hour 8: Behavioral and Resume Stories

Prepare STAR stories tied to the JD.

#### Story 1: Production support and reliability

- Situation: Stavvy Tier 2/3 support for fintech web apps.
- Task: Diagnose and resolve production issues.
- Action: Investigated integrations, logs, data flows, and stakeholder reports.
- Result: Improved reliability and reduced user-impacting issues.
- Link to Digicel: telecom systems need high availability and fast incident response.

#### Story 2: Documentation and operational continuity

- Situation: Stavvy/HRplus documentation for APIs, architecture, audits, ISO 27001.
- Task: Make systems easier to support and audit.
- Action: Created and maintained documentation for integrations and system behavior.
- Result: Better onboarding, compliance support, and maintainability.
- Link to Digicel: role emphasizes documentation, legacy stabilization, and continuity.

#### Story 3: Modernization and automation

- Situation: HRplus reporting/BI modernization and freelance CI/CD/self-hosting.
- Task: Improve maintainability and deployment consistency.
- Action: Used Docker, pipelines, and structured project setup.
- Result: Faster, more repeatable delivery.
- Link to Digicel: role includes modernization, automation, and scalable systems.

#### Story 4: Assessment project ownership

- Situation: Large requirements in short timeframe.
- Task: Deliver a complete telecom-style portal.
- Action: Broke work into modules, planned phases, implemented, tested, documented, containerized.
- Result: Working app with seeded data, Docker startup, complaint workflows, dashboard, and grounded chatbot.
- Link to Digicel: demonstrates independent ownership across SDLC.

## 30-Minute Demo Script

Use this if asked to walk through the project live.

1. **README**
   - Show project overview, Docker steps, seeded credentials, assumptions, chatbot setup.

2. **Docker**
   - Explain `docker-compose.yml` and `entrypoint.sh`.

3. **Login and roles**
   - Show `UserProfile`, `role_required`, login routing.

4. **Customer flow**
   - Customer submits complaint and views status.

5. **Agent flow**
   - Agent queue, status update, notes, escalation.

6. **Admin flow**
   - Admin list, assignment, status override, dashboard.

7. **Chatbot**
   - Show intent detection, context builder, prompt, Groq client, saved messages.

8. **Tests and docs**
   - Show chatbot/complaints tests and Documentation folder.

## Questions to Ask Them

Ask 2-3 thoughtful questions near the end.

- What systems or platforms would this role own first?
- Are the biggest challenges currently modernization, new product delivery, supportability, or performance?
- What does success look like in the first 90 days?
- How are production releases and on-call support currently structured?
- What is the current CI/CD and observability stack?

## Final Checklist Before Interview

- Run or mentally rehearse the project demo.
- Know seeded credentials and which role does what.
- Know where Docker, seed, complaint workflow, chatbot prompt/context, and tests live.
- Prepare your 90-second intro.
- Prepare three STAR stories from resume experience.
- Prepare one honest answer about AI usage:
  - AI helped with planning, implementation support, documentation, and refactoring prompts.
  - You reviewed, adjusted, debugged, tested, and can explain the code.
- Prepare improvement roadmap:
  - CI/CD, observability, pagination, configurable SLA, production hardening, more tests.

## If You Only Have 2 Hours

Prioritize:

1. 20 min: 90-second intro + resume-to-JD fit.
2. 30 min: Project architecture walkthrough.
3. 30 min: Complaint workflow + chatbot grounding.
4. 20 min: Docker/seeding/README requirements.
5. 20 min: STAR stories + questions for them.

## Key Message to Land

This project was designed to show the exact kind of work the role needs: turning a business requirement into a maintainable system, documenting choices, testing important behavior, containerizing the app for simple review, and thinking about operational support. Your background in production support, documentation, modernization, Docker, and stakeholder collaboration is directly relevant to Digicel's Software Development & Design Engineer role.
