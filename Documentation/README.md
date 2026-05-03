# Documentation

Engineering and operator docs for the **Telecom Customer Portal** assessment. Quick start (Docker, `.env`, seeded logins) lives in the repository root [`README.md`](../README.md).

| Document | Audience | Contents |
|----------|----------|----------|
| [`commands.md`](commands.md) | Developers / operators | Docker Compose, optional host Django workflow, tests, troubleshooting |
| [`technical-architecture.md`](technical-architecture.md) | Engineers | Stack, settings, apps, URLs, data model, chatbot pipeline, seeding |
| [`non-technical-overview.md`](non-technical-overview.md) | Stakeholders, QA, PM | Roles, end-to-end workflows, business rules, what the product does today |

### Module map (code)

| Area | Django app | Highlights |
|------|------------|------------|
| Auth & roles | [`accounts/`](../DigicelAssessment/accounts/) | Login, role-based home routes, `@role_required` |
| Customer domain | [`customers/`](../DigicelAssessment/customers/) | Plans, accounts, usage, payments |
| Complaints | [`complaints/`](../DigicelAssessment/complaints/) | Full lifecycle, notes, history, agent queue, admin assign/status |
| Network | [`network/`](../DigicelAssessment/network/) | `NetworkOutage` records for region-aware answers |
| Admin metrics | [`dashboard/`](../DigicelAssessment/dashboard/) | Status/category counts, average resolution time, SLA breach list |
| Chatbot | [`chatbot/`](../DigicelAssessment/chatbot/) | Sessions/messages in DB, intent detection, DB-backed context, Groq |
| Seed & utilities | [`core/`](../DigicelAssessment/core/) | `seed_data` management command |

Assessment source requirements: [`Overview and Plans/Project Overview/ProjectDescription.md`](../Overview%20and%20Plans/Project%20Overview/ProjectDescription.md).
