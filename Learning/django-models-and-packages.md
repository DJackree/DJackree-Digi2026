# Django models and Python packages (how they fit together)

This note explains two ideas that often get mixed up:

1. **Models**: Python classes that describe database tables.
2. **Packages**: folders of Python modules that Django treats as **apps** when configured correctly.

Examples below point at this repo under [`DigicelAssessment/`](../DigicelAssessment/).

---

## Part A — Django models (baby terms)

### What a model is

A **model class** is a blueprint for one database **table**:

- Each **attribute** on the class becomes a **column** (with a type like text, integer, foreign key).
- Each **row** in the table is one saved record.

Example from this project:

- [`DigicelAssessment/accounts/models.py`](../DigicelAssessment/accounts/models.py) defines `UserProfile`.
- [`DigicelAssessment/customers/models.py`](../DigicelAssessment/customers/models.py) defines `ServicePlan`, `CustomerAccount`, etc.

Baby translation:

- **Model** = “what one kind of thing looks like.”
- **Migration** = “instructions to create/update the actual DB table.”
- **ORM** = Django’s machinery that lets you read/write rows using Python instead of raw SQL.

### Relationships (the usual trio)

You’ll see three patterns constantly:

1. **`ForeignKey`** — many rows point to **one** parent row (many‑to‑one from the child side).

   Example idea: many payments belong to one customer account.

2. **`OneToOneField`** — exactly **one** row links to exactly **one** other row.

   Example in this repo: each `UserProfile` attaches to exactly one Django `User`.

3. **`ManyToManyField`** — many‑to‑many via an intermediate table (not heavily used in Phase 1 foundation models).

### Where models “go live” in the database

Changing models alone doesn’t change PostgreSQL until you:

```bash
python manage.py makemigrations
python manage.py migrate
```

This project also runs `migrate` during Docker startup via [`DigicelAssessment/entrypoint.sh`](../DigicelAssessment/entrypoint.sh).

See also: [`Learning/django-migrations.md`](django-migrations.md).

---

## Part B — Python packages and Django apps

### What “declaring a package” means in Python

A **folder** becomes an **importable Python package** when:

1. It’s on Python’s import path (your project root / installed packages).
2. It behaves like a package module—historically people added [`__init__.py`](https://docs.python.org/3/tutorial/modules.html#packages), and **you’ll still see `__init__.py` files** in Django apps for clarity and tooling even though Python 3 namespace packages exist.

Baby translation:

> A package is just **a folder of Python files that can be imported** like `import accounts`.

In this repo:

- [`DigicelAssessment/accounts/`](../DigicelAssessment/accounts/) is a package.
- [`DigicelAssessment/customers/`](../DigicelAssessment/customers/) is a package.
- [`DigicelAssessment/config/`](../DigicelAssessment/config/) is the Django **project configuration package**.

### What makes a folder a Django **app**

A Django **app** is a Python package that Django registers in **`INSTALLED_APPS`** inside [`DigicelAssessment/config/settings.py`](../DigicelAssessment/config/settings.py):

```python
INSTALLED_APPS = [
    ...
    "accounts",
    "customers",
    "core",
]
```

Each app typically contains:

- **`apps.py`** — metadata (`AppConfig`), human‑readable label.
- **`models.py`** — database models (optional but common).
- **`views.py`** — request handlers (optional).
- **`urls.py`** — routes for this app (optional).
- **`migrations/`** — migration package for schema history.

Baby translation:

> **`INSTALLED_APPS` is Django’s guest list**: “these packages are part of my website.”

### How Django discovers `models.py`

After an app is listed in `INSTALLED_APPS`, Django loads its models **when Django starts**.

That means:

- Model classes must live (directly or indirectly) under an installed app package so Django’s app registry can import them reliably.

### Import paths vs filesystem paths

These refer to the **same app**, different perspectives:

| Idea | Example |
|---|---|
| Filesystem folder | `DigicelAssessment/accounts/` |
| Python import string used by Django settings | `"accounts"` |
| URLs include string | `include("accounts.urls")` |

Baby translation:

> The folder name **`accounts`** becomes the **first part of imports** like `accounts.models`.

---

## Quick contrast table

| Concept | Question it answers |
|---|---|
| **Model** | What table/columns represent this entity? |
| **Migration** | How do we change the database safely over time? |
| **Python package** | What folder/module namespace holds code? |
| **Django app** | Which packages Django should load (`INSTALLED_APPS`)? |

---

## Tiny diagram

```text
accounts/              <-- Python package + Django app (because INSTALLED_APPS)
  models.py            <-- defines ORM models -> migrations -> PostgreSQL tables
  views.py             <-- handles HTTP responses (routing chooses view)
  urls.py              <-- maps URL paths -> views
```

---

## Practical tip for beginners

When something “doesn’t import,” check:

1. Is the app in **`INSTALLED_APPS`**?
2. Is there a typo in **`apps.py`** `name = "accounts"` vs folder name?
3. Did you remember **`makemigrations`/`migrate`** after changing models?
