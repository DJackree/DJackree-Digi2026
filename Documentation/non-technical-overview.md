# Product overview (non-technical)

This document explains **what the Telecom Customer Portal is for**, **who uses it**, and **how work is expected to flow**. It is written for stakeholders, testers, and anyone who does not need code-level detail. Technical detail lives in [`technical-architecture.md`](technical-architecture.md).

---

## What this system is

The portal is a **single place** where:

- **Customers** can look after their mobile or telecom account, **raise problems** (complaints or faults), and **see what is happening** with those issues.
- **Frontline staff (agents)** can **pick up**, **update**, and **resolve** customer issues in a consistent way.
- **Managers (admins)** can **see the whole picture**: assign work, **override** status when needed, and **measure** performance (for example, how long things take to fix and what is overdue).

A second major piece is an **AI assistant (chatbot)** that answers everyday account questions for logged-in customers, using **real information** from the system (not guesses).

The full vision is defined in the assessment brief: [`Project Overview/ProjectDescription.md`](../Project%20Overview/ProjectDescription.md). Implementation follows the phased plans under [`Plans/`](../Plans/).

---

## Who uses the system

| Role | In plain terms | Main goals |
|------|----------------|------------|
| **Customer** | Someone with a Digicel-style account | Submit and track issues; ask the chatbot about plan, balance, usage, payments, open tickets, and local outages. |
| **Agent** | Support staff who work cases | Work **their** assigned list; update status; add internal notes; escalate when needed. |
| **Admin** | Team lead or operations | See **all** cases; assign or reassign agents; move any case to any allowed state; view dashboards and reports. |

---

## Expected workflows (full product)

### Customers

1. **Log in** to a secure portal.
2. **Submit a complaint or fault** by choosing a category (for example Billing, Network, Device, Roaming, Other) and describing the problem.
3. **Track progress** on their own tickets: they can **see** status updates but **cannot** change workflow themselves.
4. **Use the chatbot** (when built) to ask things like:
   - What plan am I on?
   - What is my balance?
   - How much data have I used this month?
   - Do I have open complaints?
   - When was my last payment?
   - Are there outages in my area?

The chatbot must answer from **stored account data**. If it does not have the information, it should say so clearly rather than invent an answer.

### Agents

1. **Log in** and open a **queue of cases assigned to them**, ordered so older issues are easy to spot.
2. Open a case and **update status** along an agreed path (see **Business rules** below).
3. Add **internal notes** (and resolution notes where appropriate). Customers should **not** see internal notes meant for staff.
4. **Escalate** when the issue needs more attention, and give a **reason** for escalation.

Agents should **only** work on cases assigned to them unless product rules later allow exceptions.

### Admins

1. **Log in** and see **all** complaints.
2. **Assign or reassign** a case to an agent.
3. **Change status** when necessary, including situations that do not fit the normal agent path.
4. Use a **dashboard** that summarizes:
   - How many complaints are in each status.
   - How many fall into each category.
   - Typical time to resolve.
   - Which cases are **past the agreed time limit** (SLA) and still open.

Admins may also **manage users** (often via an admin tool built into the product).

---

## Business rules (complaints)

These rules reflect the assessment specification.

### Status lifecycle

Every complaint moves through this path:

**Open → In Progress → Escalated → Resolved → Closed**

- **Agents** move cases **forward** along this path (they do not skip arbitrarily; escalation requires a reason).
- **Admins** can set **any** status when the business needs it (for example clearing a backlog or correcting a mistake).
- **Customers** only **view** status; they do not change it.

### Service level (SLA) idea

The business expects issues not to sit open forever. The assessment uses a simple rule: a case that has been open **too long** (for example more than **five days**) while still not **resolved** or **closed** is treated as **breaching** the SLA. The admin dashboard should highlight those cases so leaders can act.

*Exact SLA days and wording can be tuned in implementation; the plan assumes five days unless a document says otherwise.*

### Sensitive information

- **Internal notes** are for staff. Customers should not see them on the customer-facing screens.
- The chatbot should receive **only the data needed** to answer a question, to protect customer privacy.

---

## Data the business cares about (conceptual)

For each customer account, the system is expected to know (or be seeded with demo values):

- **Account identity** and **region** (useful for outage messaging).
- **Current plan** (name, allowances).
- **Balance** and **recent payments**.
- **Usage** for the current period (for example data used this month).
- **Complaints** linked to that account (status, category, timeline).

For **network issues affecting an area**, the system may hold **outage or fault records** tied to a region so customers and the chatbot can get an accurate answer.

---

## What you can use today vs what comes next

**Today (foundation phase):**

- The **database** and **admin website** can hold users, roles (customer / agent / admin), service plans, customer accounts, usage snapshots, and payments.
- **Demo data** can be loaded with a seed command so reviewers can log in and inspect records.

**Still to build** (per project plans):

- Customer, agent, and admin **web pages** (forms, queues, dashboard charts).
- **Complaint** records, assignment, workflow, and SLA views.
- **Chatbot** screen and connection to the AI provider (Groq) with strict “answer only from real data” behavior.
- **One-command Docker** startup that runs the web app, migrations, and first-time seed automatically.

If you are testing or demonstrating the product, use [`Documentation/commands.md`](commands.md) for the exact commands. For technical behavior of the current code, use [`technical-architecture.md`](technical-architecture.md).
