You are a senior software architect tasked with converting a product specification into a complete, structured implementation plan suitable for a 3–4 day take-home technical assessment.

The input file (`ProjectDescription.md`) contains a high-level description of a Telecom Customer Portal system. Your task is to transform this specification into a **detailed, execution-ready implementation plan**.

---

# 🎯 Objective

Generate a **comprehensive implementation plan in markdown** that demonstrates:

* Clear architectural thinking
* Strong backend design (Django + PostgreSQL)
* Practical scoping for a 3–4 day timeline
* Clean separation of concerns
* Thoughtful tradeoffs and assumptions

This plan should reflect how an experienced engineer would approach building the system efficiently while meeting all stated requirements.

---

# ⚙️ Key Instructions

## 1. Decompose the System into Modules

Identify all major modules from the specification. At minimum:

* Complaint & Fault Management System
* AI Customer Chatbot

Break each module into **logical sections/features**.

---

## 2. For EACH Section, Use Phased Development

Every section MUST be broken down into the following **four phases**:

### Phase 0 — Design

* Define purpose of the section
* Identify entities and relationships
* Define business rules and constraints
* Call out ambiguities and assumptions
* Justify design decisions

### Phase 1 — Database

* Define Django models (fields, relationships)
* Explain why each field exists
* Include constraints (FKs, nullability, indexes if needed)
* Mention migrations

### Phase 2 — API

* Define endpoints (URL, method)
* Request/response structure
* Authentication/authorization rules
* Validation logic
* Error handling strategy

### Phase 3 — UI

* Define pages/components
* User flows
* Role-based behavior differences
* Key UI interactions (forms, tables, dashboards)

---

## 3. Define Global Architecture

Before module breakdown, include:

### System Architecture

* Django + PostgreSQL + Docker Compose setup
* Service structure (web, db, etc.)
* High-level request flow

### Authentication & Authorization Strategy

* Role system (Customer, Agent, Admin)
* How Django auth will be used
* Permission enforcement approach

### Data Modeling Strategy

* Core entities across the system
* Relationships between them
* Any normalization decisions

---

## 4. Define Critical System Logic

Explicitly design:

### Complaint Workflow

* Allowed state transitions
* Role-based restrictions
* Validation rules

### SLA Logic

* How SLA is calculated
* How breaches are detected

### Chatbot Architecture (VERY IMPORTANT)

You MUST:

* Avoid overengineering (no RAG, no vector DB)
* Use a simple, deterministic approach:

  1. Intent detection (rule-based or keyword-based)
  2. Database query
  3. Context construction
  4. LLM prompt design
* Define how hallucination is prevented
* Show example prompt structure

---

## 5. Define API Surface

List all major endpoints across the system:

* Complaints
* Dashboard
* Chatbot

Include:

* HTTP methods
* URL structure
* Purpose

---

## 6. Define Seed Data Strategy

* What data is required
* How it will be generated
* How it runs automatically on first Docker startup

---

## 7. Define Development Plan (Execution Order)

Break implementation into phases:

* Phase 0 — Design
* Phase 1 — Foundation (setup, auth, docker)
* Phase 2 — Core features
* Phase 3 — Business logic
* Phase 4 — UI & dashboard
* Phase 5 — Chatbot

Each phase should:

* Be realistic for a 3–4 day timeline
* Build incrementally
* Avoid rework

---

## 8. Explicitly State Assumptions

For any ambiguity in the spec:

* Make a reasonable assumption
* Clearly document it

---

## 9. Optimize for Assessment Success

The plan should:

* Avoid unnecessary complexity (no microservices, no external auth systems)
* Favor Django-native solutions
* Be easy for a reviewer to run and understand
* Demonstrate strong backend fundamentals

---

# 🧠 Thinking Expectations

While generating the plan, you should:

* Infer missing details from the spec
* Make pragmatic engineering decisions
* Prefer simplicity over theoretical completeness
* Justify key choices (especially around data modeling and chatbot design)

---

# 📌 Output Requirements

* Output must be in **clean, well-structured markdown**
* Use headings, sections, and code blocks
* Include sample Django model snippets where relevant
* Include example API payloads where useful
* Be detailed but practical (not academic)

---

# 🚫 Constraints

* Do NOT introduce technologies outside the required stack
* Do NOT use Supabase or external auth providers
* Do NOT design for production-scale complexity
* Do NOT use vector databases or advanced AI pipelines

---

# ✅ Final Goal

Produce a plan that:

* Could be followed step-by-step to build the system
* Demonstrates clear engineering thinking
* Aligns tightly with the provided requirements
* Maximizes scoring in a technical assessment

---

Now analyze the attached `ProjectDescription.md` and generate the full implementation plan.
