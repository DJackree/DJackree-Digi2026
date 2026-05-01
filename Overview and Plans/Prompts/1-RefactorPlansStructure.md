You are a senior software architect and implementation planner.

I have a Django/PostgreSQL/Docker technical assessment project for a Telecom Customer Portal. The current `Plans/` folder contains several planning documents, but I want to restructure them so each feature/module has its own implementation-focused document.

Your task is to refactor the planning documents, not implement code.

## Source Documents

Use the existing documents in `Plans/`:

- `Plans/00-master-implementation-plan.md`
- `Plans/01-system-architecture-plan.md`
- `Plans/02-complaint-and-fault-management-plan.md`
- `Plans/03-ai-customer-chatbot-plan.md`
- `Plans/04-execution-and-delivery-plan.md`
- `Plans/05-api-seed-and-submission-plan.md`
- `Plans/README.md`

Also reference:

- `Project Overview/ProjectDescription.md`
- `Prompts/InitalPrompt.md`

## Restructure Goal

Reorganize the plans so there are only three feature/module implementation plans plus one master plan.

The final `Plans/` folder should contain:

1. `00-master-implementation-plan.md`
2. `01-system-architecture-plan.md`
3. `02-complaint-and-fault-management-plan.md`
4. `03-ai-customer-chatbot-plan.md`
5. `README.md`

Delete or consolidate the content from:

- `04-execution-and-delivery-plan.md`
- `05-api-seed-and-submission-plan.md`

Their useful content should be moved into `00-master-implementation-plan.md` or the relevant feature plan.

## Responsibility Of Each Document

### `00-master-implementation-plan.md`

This should become the high-level master delivery plan.

It should include:

- Project overview
- Full system scope
- Overall architecture summary
- Technology stack
- Global assumptions
- Cross-cutting decisions
- Overall implementation order
- 3-4 day delivery timeline
- Seed data strategy summary
- README/submission checklist
- Risk register
- Manual verification checklist
- How the individual implementation plans relate to each other

This document should consolidate anything that is not specific to one feature/module.

Move content from the old execution/delivery plan and API/seed/submission plan here where appropriate.

Do not duplicate detailed feature implementation steps that belong in the module plans.

---

### `01-system-architecture-plan.md`

This should be the implementation plan for the project foundation.

It should cover everything needed to set up:

- Django project
- Django apps
- PostgreSQL database
- Docker and Docker Compose
- Environment variables
- Entry point/startup flow
- Automatic migrations
- Authentication
- User roles
- `UserProfile`
- Role helpers/decorators
- Base templates/layout
- Role-based landing redirects
- Initial admin registration
- `.env.example`
- README foundation instructions

This document should not implement complaint-specific workflows or chatbot-specific logic, except where placeholders/app structure are needed.

Break this document into these phases:

## Phase 1 - Database Setup

Include:

- Required apps
- Models needed for foundation, especially `UserProfile`
- Fields and rationale
- Relationships
- Constraints
- Indexes
- Migrations
- PostgreSQL configuration
- Environment variables
- Docker database service

## Phase 2 - API/Backend Setup

Include:

- Django project creation
- App registration
- Settings configuration
- URL routing
- Auth views
- Login/logout
- Role-based redirect
- Role helper functions/decorators
- Authorization behavior
- Docker web service
- Entrypoint flow
- Migration startup command
- Error handling

## Phase 3 - UI Setup

Include:

- Base Bootstrap layout
- Login page
- Logout behavior
- Role-specific landing pages
- Navigation
- Flash messages
- Basic templates directory structure
- UI acceptance criteria

Each phase should include:

- Purpose
- Files to create/update
- Implementation tasks
- Acceptance criteria
- Risks or notes

---

### `02-complaint-and-fault-management-plan.md`

This should be the implementation plan for the Complaint & Fault Management module.

It should build on the architecture from `01-system-architecture-plan.md`.

It should cover:

- Customer complaint submission
- Customer complaint history/detail
- Complaint categories
- Complaint statuses
- Complaint workflow
- Agent assigned queue
- Agent status updates
- Agent internal notes
- Agent escalation
- Admin all-complaints view
- Admin assignment/reassignment
- Admin status override
- Complaint status history
- SLA threshold logic
- Dashboard metrics
- Network outage/fault records
- Seed data required for complaints and outages
- Manual tests for customer/agent/admin complaint flows

Break this document into these phases:

## Phase 1 - Database Setup

Include:

- Complaint model
- ComplaintNote model
- ComplaintStatusHistory model
- NetworkOutage model
- Any required customer/account relationships
- Status/category choices
- Field rationale
- Constraints
- Indexes
- Migrations
- Seed data needed for this module

## Phase 2 - API/Backend Setup

Include:

- Customer routes/views/forms
- Agent routes/views/forms
- Admin routes/views/forms
- Workflow service
- SLA service
- Dashboard query service
- Permission checks
- Validation rules
- Error handling
- URL structure
- Request/response examples where useful

## Phase 3 - UI Setup

Include:

- Customer complaint list/detail/create pages
- Agent queue and complaint detail pages
- Agent note/status/escalation forms
- Admin complaint list/detail pages
- Admin assignment/status forms
- Admin dashboard
- SLA breach display
- Role-based UI differences
- Manual UI acceptance criteria

Each phase should include:

- Purpose
- Files to create/update
- Implementation tasks
- Acceptance criteria
- Risks or notes

---

### `03-ai-customer-chatbot-plan.md`

This should be the implementation plan for the AI Customer Chatbot module.

It should build on the architecture and complaint/customer data from plans `01` and `02`.

It should cover:

- Chat sessions
- Chat messages
- Conversation history
- Rule-based intent detection
- Customer-scoped context builders
- Account plan lookup
- Balance lookup
- Monthly usage lookup
- Open complaint lookup
- Last payment lookup
- Active outage lookup
- Groq API integration
- `llama-3.1-8b-instant`
- Prompt design
- Hallucination prevention
- Sensitive data handling
- Chat UI
- Suggested questions
- Seed data needed for chatbot answers
- Manual tests for all supported questions

Break this document into these phases:

## Phase 1 - Database Setup

Include:

- ChatSession model
- ChatMessage model
- Any customer/account/payment/usage data dependencies
- Fields and rationale
- Relationships
- Constraints
- Indexes
- Migrations
- Seed data dependencies

## Phase 2 - API/Backend Setup

Include:

- Intent detection service
- Context builder service
- Groq client wrapper
- Prompt builder
- Chat routes/views
- Message endpoint
- Session creation
- Permission checks
- Validation rules
- Error handling
- Request/response examples
- Hallucination prevention strategy

## Phase 3 - UI Setup

Include:

- Chat page
- Message transcript
- Text input
- Send button
- Suggested question buttons
- Loading state
- Error state
- Role-based access
- Manual UI acceptance criteria

Each phase should include:

- Purpose
- Files to create/update
- Implementation tasks
- Acceptance criteria
- Risks or notes

---

## README.md

Update `Plans/README.md` so it explains the new structure:

- Master plan first
- Foundation plan second
- Complaint/fault module third
- Chatbot module fourth

It should explain that each module plan is implementation-focused and broken into:

1. Phase 1 - Database Setup
2. Phase 2 - API/Backend Setup
3. Phase 3 - UI Setup

## Important Requirements

- Do not remove useful information from old documents. Consolidate it into the correct remaining document.
- Avoid duplicating large sections across documents.
- Make each implementation plan execution-ready.
- Each plan should include concrete files to create/update.
- Each plan should include acceptance criteria.
- Each plan should include manual verification steps.
- Keep the stack limited to Django, PostgreSQL, Docker Compose, Bootstrap templates, and Groq.
- Do not introduce Supabase, external auth providers, vector databases, RAG, microservices, or unnecessary infrastructure.
- Preserve the deterministic chatbot design:
  1. Intent detection
  2. Database query
  3. Context construction
  4. LLM prompt
- Make sure the chatbot explicitly avoids hallucination and answers only from context.
- Make sure the Docker startup flow includes migrations and automatic first-run seeding.
- Make sure the final plans still align with the original assessment requirements.

## Output Expectations

After restructuring, report:

- Which files were updated
- Which files were removed
- Where the old `04` and `05` content was consolidated
- Any assumptions made
- Any questions or risks remaining

Do not implement the application code. Only restructure the planning documents.