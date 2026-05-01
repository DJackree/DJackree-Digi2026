# Technical Assessment: Telecom Customer Portal
### Software Development & Design Engineer — Take-Home Project

---

## Overview

You have been asked to design and build a small but complete web application that reflects the kind of work you would be doing in this role. The application has two core modules:

1. **A Complaint & Fault Management System** — for customers to submit and track complaints, and for internal agents/admins to manage them through a defined workflow
2. **An AI-Powered Customer Chatbot** — for logged-in customers to ask natural language questions about their account and receive accurate, data-driven responses

The goal of this assessment is not simply to see if you can build something that works. We are looking at **how** you build it — your architecture decisions, code quality, database design, documentation, and your ability to deliver a coherent, well-structured system independently.

---

## Technology Requirements

You **must** use the following technologies. Submissions that do not meet these requirements will not be evaluated.

| Requirement | Detail |
|---|---|
| **Backend** | Python 3.x, Django |
| **Frontend** | Django templates with Bootstrap, and/or React |
| **Database** | PostgreSQL |
| **Containerisation** | Docker & Docker Compose — the entire application must run with a single `docker compose up --build` command for the first run or `docker compose up` for subsequent runs |
| **LLM Integration** | Groq API (free tier — no credit card required) |
| **Version Control** | GitHub or Bitbucket — submit a link to your repository |

---

## Module 1 — Complaint & Fault Management System

### User Roles

The system must support three distinct user roles:

- **Customer** — can submit complaints, view their own complaint history, and track status updates
- **Agent** — can view and manage complaints assigned to them, update statuses, and add resolution notes
- **Admin** — has full visibility of all complaints, can assign complaints to agents, manage users, and view reports

### Complaint Workflow

All complaints must move through the following status lifecycle:

**Open → In Progress → Escalated → Resolved → Closed**

- Agents can move complaints forward through the workflow
- Admins can move complaints to any status, including escalation
- Customers can only view status — they cannot change it

### Complaint Fields

Each complaint record should capture at minimum:

- Customer account reference
- Complaint category (e.g. Billing, Network, Device, Roaming, Other)
- Description of the issue
- Submission date and time
- Current status
- Assigned agent
- Internal notes / resolution notes (visible to agents and admins only)
- Last updated timestamp

### Admin Dashboard

The admin interface should include a summary dashboard showing:

- Total complaints by status
- Total complaints by category
- Average resolution time (from Open to Resolved)
- A list of complaints breaching a defined SLA threshold (e.g. open for more than 5 days)

### Agent Interface

Agents should have a clean working view showing:

- Complaints assigned to them, sorted by age
- Ability to update status and add notes
- Ability to flag a complaint for escalation with a reason

---

## Module 2 — AI Customer Chatbot

### Overview

Logged-in customers should have access to a chat interface where they can ask natural language questions about their account. The chatbot must respond using **real data from the database** — it must not guess, fabricate, or hallucinate account information.

### Example Questions the Chatbot Should Handle

- *"What plan am I currently on?"*
- *"What is my current account balance?"*
- *"How much data have I used this month?"*
- *"Do I have any open complaints?"*
- *"When was my last payment made?"*
- *"Are there any active faults or outages affecting my area?"*

### Technical Expectations

- The chatbot must retrieve relevant account data from the database and pass it to the LLM as context
- The LLM should be explicitly instructed via your system prompt to answer **only from the provided context** and to clearly state when it does not have enough information to answer
- Conversation history should be maintained within a session so the chatbot can handle follow-up questions naturally
- Sensitive account data should be handled carefully — do not pass unnecessary data into prompts

### LLM API

You must use the **Groq API** with the `llama-3.1-8b-instant` model.

- **Groq** — get a free API key (no credit card required) at [https://console.groq.com](https://console.groq.com)
- The free tier provides generous rate limits — more than sufficient for development and testing
- Use the `groq` Python SDK (`pip install groq`)

Any API keys or secrets must **never** be hardcoded in your source code. All sensitive configuration must be managed via environment variables in a `.env` file (see submission instructions below).

> **Note:** Your submitted `.env` file must include a working `GROQ_API_KEY`. The reviewer will use this key to test the chatbot during evaluation.

---

## Seeded Data Requirements

Your application must include a Django management command or fixture that seeds the database with realistic sample data, including:

- At least **5 customer accounts** with profile information, current plan, balance, and usage data
- At least **3 agent accounts** and **1 admin account**
- At least **15 complaints** distributed across different statuses, categories, and agents
- At least **3 service plans** (e.g. Basic, Standard, Premium) with associated data/call/SMS allowances
- At least **2 simulated network fault/outage records** tied to a region or area

This seeded data **must load automatically** when the application is started for the first time via `docker compose up --build`. The reviewer should not need to run any manual seeding command — if the database is empty on startup, the application must seed it automatically.

---

## Docker Requirements

- The entire application — Django, PostgreSQL, and any other services — must be fully containerised using **Docker Compose**
- Running `docker compose up` (or `docker compose up --build` on first run) must bring up the complete application with no additional manual steps beyond configuring the `.env` file
- Database migrations should run automatically on container startup
- Seed data must run automatically on first startup — the reviewer must not need to run any manual command to populate the database
- The application should be accessible at `http://localhost:8000` after startup

---

## README Requirements

Your repository must include a `README.md` file at the root level. It must cover:

1. **Project Overview** — a brief description of what the application does
2. **Prerequisites** — what needs to be installed before running (Docker, Docker Compose, etc.)
3. **Environment Setup** — how to configure the `.env` file (list all required variables with descriptions, but no actual values)
4. **How to Run** — step-by-step instructions to get the application running from a fresh clone
5. **How to Seed the Database** — explain how seeding is handled automatically on first run
6. **Default Login Credentials** — the seeded usernames and passwords for each role (customer, agent, admin) so the reviewer can log in immediately
7. **Chatbot Setup** — any specific steps required to enable the AI chatbot
8. **Assumptions & Design Decisions** — a short section explaining any notable choices you made or assumptions you relied on where requirements were not explicit

---

## Submission Instructions

Please submit your assessment by emailing the following to **ashley.ramdin@digicelgroup.com**:

1. **GitHub/Bitbucket Repository Link** — your repository must be public. Ensure your commit history is intact — we want to see how you worked, not just the final result

2. **`.env` file** — attach your configured `.env` file as a plain `.txt` file (e.g. `env_config.txt`) containing all environment variables with their actual values, including your `GROQ_API_KEY`. This file must **not** be committed to your repository

3. **AI Usage Document** *(if applicable)* — if you used any AI tools (ChatGPT, Claude, Copilot, etc.) to assist in writing your code, attach a Word document (`.docx`) listing the prompts you used and which parts of the code they helped produce. There is no penalty for using AI tools — we ask for transparency so we can assess your understanding of the code you submit. You will be expected to walk through and explain your code during the follow-up technical interview

---

## Time Expectation

This assessment is designed to be completed in approximately **3-4 days**. You do not need to build a production-grade system — we are looking for clean, thoughtful work within a reasonable timeframe. Prioritise correctness, clarity, and completeness.

If you have any questions about the requirements, please reach out to **ASHLEY RAMDIN** at **ashley.ramdin@digicelgroup.com** before beginning.

---

*Good luck — we look forward to reviewing your submission.*
