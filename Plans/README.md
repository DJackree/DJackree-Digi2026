# Plans Index

These documents convert `Project Overview/ProjectDescription.md` into an implementation-ready plan for the Telecom Customer Portal assessment.

The plan set is intentionally ordered. Start with the master plan for delivery context, then implement each module plan in sequence.

## Final Structure

1. `00-master-implementation-plan.md`
2. `01-system-architecture-plan.md`
3. `02-complaint-and-fault-management-plan.md`
4. `03-ai-customer-chatbot-plan.md`
5. `README.md`

## Reading Order

### 1. Master Implementation Plan

`00-master-implementation-plan.md` is the high-level delivery plan. It includes:

- Project overview.
- Full system scope.
- Overall architecture summary.
- Technology stack.
- Global assumptions.
- Cross-cutting decisions.
- Overall implementation order.
- 3-4 day delivery timeline.
- Seed data strategy summary.
- README and submission checklist.
- Risk register.
- Manual verification checklist.
- How the individual implementation plans relate to each other.

Content from the previous execution/delivery and API/seed/submission plans has been consolidated here.

### 2. System Architecture Implementation Plan

`01-system-architecture-plan.md` covers everything needed to set up the project foundation:

- Django project and apps.
- PostgreSQL database.
- Docker and Docker Compose.
- Environment variables.
- Entrypoint/startup flow.
- Automatic migrations.
- Authentication.
- User roles.
- `UserProfile`.
- Role helpers/decorators.
- Shared customer account data.
- Base templates/layout.
- Role-based landing redirects.
- Initial admin registration.
- README foundation instructions.

### 3. Complaint And Fault Management Implementation Plan

`02-complaint-and-fault-management-plan.md` builds on the foundation plan and implements:

- Customer complaint submission.
- Customer complaint history/detail.
- Complaint categories and statuses.
- Complaint workflow.
- Agent assigned queue.
- Agent notes, status updates, and escalation.
- Admin all-complaints view.
- Admin assignment/reassignment.
- Admin status override.
- Complaint status history.
- SLA threshold logic.
- Dashboard metrics.
- Network outage/fault records.
- Complaint and outage seed data.

### 4. AI Customer Chatbot Implementation Plan

`03-ai-customer-chatbot-plan.md` builds on the architecture and complaint/customer data plans and implements:

- Chat sessions.
- Chat messages.
- Conversation history.
- Rule-based intent detection.
- Customer-scoped context builders.
- Plan, balance, usage, open complaint, last payment, and outage lookup.
- Groq API integration with `llama-3.1-8b-instant`.
- Prompt design.
- Hallucination prevention.
- Sensitive data handling.
- Chat UI.
- Suggested questions.

## Implementation Phase Structure

Each implementation plan is broken into:

1. Phase 1 - Database Setup
2. Phase 2 - API/Backend Setup
3. Phase 3 - UI Setup

Each phase includes:

- Purpose.
- Files to create or update.
- Implementation tasks.
- Acceptance criteria.
- Risks or notes.
- Manual verification steps where relevant.

## Constraints Preserved

- Use Django, PostgreSQL, Docker Compose, Bootstrap templates, and Groq.
- Do not introduce Supabase.
- Do not use external auth providers.
- Do not use vector databases, RAG, embeddings, autonomous SQL, or microservices.
- Keep chatbot behavior deterministic:
  1. Intent detection.
  2. Database query.
  3. Context construction.
  4. LLM prompt.
- Ensure Docker startup includes migrations and automatic first-run seeding.
- Ensure chatbot answers only from provided context and refuses unsupported questions.
