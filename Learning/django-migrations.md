# How Django migrations work (concept + this project)

This note explains **migrations**: how Django turns your Python **models** into real **database tables**, and how changes stay in sync over time.

## What problem migrations solve

Your models (for example `UserProfile`, `CustomerAccount`) describe **what data should exist**.

PostgreSQL stores data in **tables with columns**.

Migrations are **versioned scripts** Django generates from model changes so everyone’s database schema matches the code—today and after future edits.

Baby translation:

- Models = **blueprints**.
- Database tables = **the actual shelves**.
- Migrations = **step‑by‑step instructions** for building/updating those shelves safely.

## The two commands you see most

### `makemigrations`

Reads your models and writes new migration files under each app’s `migrations/` folder (for example [`DigicelAssessment/accounts/migrations/`](../DigicelAssessment/accounts/migrations/), [`DigicelAssessment/customers/migrations/`](../DigicelAssessment/customers/migrations/)).

Example mental output:

```text
“Create table accounts_userprofile …”
```

You run this **when you change models** (new fields, new models, constraints, indexes).

### `migrate`

Applies pending migrations to the database:

1. Django checks which migrations have already run (stored in DB table `django_migrations`).
2. It runs only what’s missing, **in dependency order**.
3. Your PostgreSQL schema ends up matching your models.

You run this **after pulling code**, **after adding migrations**, or on **fresh databases**.

This project also runs migrate automatically on container startup via [`DigicelAssessment/entrypoint.sh`](../DigicelAssessment/entrypoint.sh).

## What’s inside a migration file?

Migration files are Python modules that describe operations such as:

- `CreateModel`
- `AddField`
- `AlterField`
- `DeleteModel`
- `AddIndex`

They include:

- **`dependencies`**: which migrations must run first (ordering matters).
- **`operations`**: the actual schema steps.

Think of each migration as one commit to your database layout.

## Initial vs future migrations

### Initial migration (`0001_initial.py`)

Usually creates tables from scratch on an empty database.

Example files in this repo:

- [`DigicelAssessment/accounts/migrations/0001_initial.py`](../DigicelAssessment/accounts/migrations/0001_initial.py)
- [`DigicelAssessment/customers/migrations/0001_initial.py`](../DigicelAssessment/customers/migrations/0001_initial.py)

### Later migrations (`0002_...py`, `0003_...py`, …)

Each file represents another incremental change.

Keeping migrations **small and sequential** makes rollbacks/reviews easier.

## How Django remembers what ran

PostgreSQL stores Django’s migration history in tables Django manages, notably:

- **`django_migrations`**: records applied migrations.

That’s why running `migrate` twice usually does nothing the second time: Django sees those entries already exist.

## Common workflows

### Fresh clone / empty database

```bash
python manage.py migrate
```

(Optional seed step next—this project uses `seed_data`.)

### You changed models locally

```bash
python manage.py makemigrations
python manage.py migrate
```

### Production-ish discipline

- Commit migration files to Git (they’re code artifacts teammates need).
- Avoid editing old migrations once teammates have applied them unless you know how to coordinate replacements.

## Things migrations do **not** do (by themselves)

- **Business seed content** beyond what you encode in migrations (fixtures/data migrations are optional patterns).
  - This project seeds demo rows via [`DigicelAssessment/core/management/commands/seed_data.py`](../DigicelAssessment/core/management/commands/seed_data.py), not migrations.

- **Automatic backups**.
  - Destructive operations (drops/renames) can lose data—plan carefully.

## Pitfalls (baby terms)

- **Model changed but no migration**: DB doesn’t match code → weird runtime errors.
- **Migration conflicts**: two branches created different `0002` files → merge carefully.
- **Wrong DB credentials/env**: migrate connects to PostgreSQL via [`DigicelAssessment/config/settings.py`](../DigicelAssessment/config/settings.py); wrong host/password looks like “migrate fails,” not “Django is broken.”

## Mental model diagram

```text
models.py + historical migrations
           |
           v
      migrate applies pending ops
           |
           v
     PostgreSQL schema + django_migrations ledger
```

## Where this shows up in Docker startup

[`DigicelAssessment/entrypoint.sh`](../DigicelAssessment/entrypoint.sh) runs:

```bash
python manage.py migrate --noinput
```

So containers apply migrations automatically before starting the server.
