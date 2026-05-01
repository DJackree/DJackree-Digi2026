# Django template tags: `nav_tags` (concept + this project)

This note explains **custom template tags**: small Python helpers you **`{% load %}`** in templates to compute values or render snippets.

Examples reference [`DigicelAssessment/accounts/templatetags/nav_tags.py`](../DigicelAssessment/accounts/templatetags/nav_tags.py) and [`DigicelAssessment/templates/base.html`](../DigicelAssessment/templates/base.html).

Related topics:

- **[`Learning/django-views.md`](django-views.md)** — `request.user` and authentication context.
- **[`Learning/forms.md`](forms.md)** — forms are unrelated but often live near templates.

---

## Why custom tags exist

Templates should stay **mostly declarative** (HTML + variables).  
Sometimes you need logic that is:

- awkward to express in pure template syntax, or
- repeated in many templates.

Custom tags put that logic in **Python**, once, with tests if you want.

Baby translation:

> **Templates paint the page; template tags fetch the paint.**

---

## Package layout (required by Django)

For an app called **`accounts`**, Django discovers tags under:

```text
accounts/
  templatetags/
    __init__.py      # can be empty; marks a Python package
    nav_tags.py      # your tag definitions
```

Then in any template:

```django
{% load nav_tags %}
```

Django imports **`accounts.templatetags.nav_tags`**.

---

## Simple tags vs inclusion tags

### `simple_tag`

Returns a **value** you assign:

```django
{% safe_user_profile user as portal_profile %}
{% if portal_profile %} ... {% endif %}
```

Good for: **one computed object** without rendering a whole partial template.

### `inclusion_tag`

Renders **another template** with a context dict.

Good for: **reusable HTML chunks** (cards, menus).

This project uses **`simple_tag`** only.

---

## This project: `safe_user_profile`

The navbar needs **`user.profile`** for role-based links.

Problem: on a **`User`**, the reverse one-to-one **`profile`** may **not exist**. Accessing `user.profile` can raise **`DoesNotExist`**.

**`safe_user_profile`** catches that case and returns **`None`** so **`base.html`** can branch without crashing:

```django
{% safe_user_profile user as portal_profile %}
...
{% if portal_profile %}
  {# show role nav #}
{% elif user.is_authenticated %}
  {# show “profile missing” warning #}
{% else %}
  {# anonymous nav #}
{% endif %}
```

---

## Alternatives (tradeoffs)

| Approach | Pros | Cons |
|----------|------|------|
| **`simple_tag`** (this repo) | Explicit; local to templates that need it | One DB-touch per render if not cached |
| **Context processor** | Always available in every template | Runs on *every* response |
| **Middleware attaching `request.profile`** | Centralized | Still must handle missing rows |

For a small assessment app, **`simple_tag`** is easy to reason about.

---

## Quick checklist when adding a new tag file

1. Create **`templatetags/`** package (`__init__.py`).
2. Add **`your_tags.py`** with `register = template.Library()`.
3. Decorate functions with **`@register.simple_tag`** (or **`inclusion_tag`**, etc.).
4. **`{% load your_tags %}`** at top of templates that use it.
5. Restart dev server if tags don’t appear (Django caches discovery in some setups).

---

## Where to read next in this repo

| Piece | File |
|-------|------|
| Tag implementation | [`DigicelAssessment/accounts/templatetags/nav_tags.py`](../DigicelAssessment/accounts/templatetags/nav_tags.py) |
| Navbar usage | [`DigicelAssessment/templates/base.html`](../DigicelAssessment/templates/base.html) |
