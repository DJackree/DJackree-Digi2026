# Product overview (non-technical)

This document explains **what the Telecom Customer Portal does**, **who uses it**, and **how work flows** day to day. Technical detail lives in [`technical-architecture.md`](technical-architecture.md). Commands for running and testing are in [`commands.md`](commands.md).

The original assessment brief: [`Overview and Plans/Project Overview/ProjectDescription.md`](../Overview%20and%20Plans/Project%20Overview/ProjectDescription.md).

---

## What this system is

The portal is a **single place** where:

- **Customers** manage their account view, **submit and track complaints**, and use an **AI chatbot** that answers from **real database data** (plan, balance, usage, payments, open complaints, regional outages).
- **Agents** work **their assigned queue**: update status along the allowed path, add **internal** notes, and **escalate** with a reason when needed.
- **Admins** see **all complaints**, **assign** work, set **any status**, and open a **dashboard** with counts by status and category, **average time to resolve**, and tickets **past the SLA window** while still open.

---

## Who uses the system

| Role | In plain terms | Main goals |
|------|----------------|------------|
| **Customer** | Account holder | Submit and track their complaints; ask the chatbot account and outage questions. |
| **Agent** | Support staff | Work assigned tickets only; move status forward; document internally; escalate. |
| **Admin** | Operations / lead | Full visibility; assignment; any status; metrics and SLA breach visibility. |

---

## What you can do in the application today

After [Docker setup](../README.md) and login:

### Customers

- Land on the **customer home** and open **My complaints** (list, create, read status on their tickets).
- Open **Chatbot** and ask questions such as plan, balance, usage this month, open complaints, last payment, outages in their area, and plan comparison prompts supported by seeded data (the bot is limited to what is in context for each intent).

### Agents

- Open the **agent home** and **complaint queue** (assigned tickets, oldest first by product design).
- On a ticket: **change status** (only allowed forward steps), add **internal notes**, **escalate** with a reason.

### Admins

- Open **admin portal** home, **complaint list** (all references), **assign** agents, **set any status**.
- Open the **dashboard**: totals by **status** and **category**, **average resolution** time (from Open to Resolved), and a **breach list** for tickets open or in progress too long (see business rules).

### Staff

- Use Django **`/admin/`** for raw model management if needed (same database as the portal).

---

## Business rules (complaints)

### Status lifecycle

Every complaint moves through:

**Open → In Progress → Escalated → Resolved → Closed**

- **Agents** advance along **allowed forward** steps only and only on **their** assigned tickets.
- **Admins** may set **any** status (for example to correct workflow or clear backlog).
- **Customers** **see** status on their tickets but **cannot** change workflow.

### Service level (SLA)

The implementation flags tickets that are **not** Resolved or Closed and have been open longer than **five days** as **SLA breaches** for the admin dashboard (see [`technical-architecture.md`](technical-architecture.md) for where this is calculated).

### Sensitive information

- **Internal notes** are for staff; customer-facing complaint views should not expose them.
- The chatbot is built to pass **only the context needed** for the detected question types—not a full dump of every table field unless required for an answer.

---

## Data the business cares about (conceptual)

For each customer account, the system holds (including demo seed values):

- **Account identity**, **region** (for outage relevance).
- **Service plan** (allowances, price).
- **Balance** and **payments** (including “last payment” style answers).
- **Usage** for a billing-style window (for “data this month” style questions).
- **Complaints** linked to the account (status, category, timeline, assignment).

**Network outages** are stored **by region** so customers (via the chatbot) can get accurate answers about active or recent issues in their area.

---

## Demo data

On **first** application startup with an **empty** database, the stack runs **`seed_data --if-empty`** automatically (Docker entrypoint). That creates multiple customers, agents, one admin, plans, accounts, usage, payments, a set of complaints across statuses, and sample outages—so reviewers can log in immediately. Credentials: root [`README.md`](../README.md).

If users already exist, seeding **skips**; reset the database volume if you need a full re-seed (see [`commands.md`](commands.md)).
