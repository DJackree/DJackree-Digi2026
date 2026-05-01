# Django forms (concept + this project)

This note explains **forms**: how Django validates incoming POST data and renders HTML fields for `<form>` submissions.

Examples reference [`DigicelAssessment/accounts/forms.py`](../DigicelAssessment/accounts/forms.py) and the login template [`DigicelAssessment/templates/accounts/login.html`](../DigicelAssessment/templates/accounts/login.html).

Related topics:

- **[`Learning/django-views.md`](django-views.md)** — views render templates and receive POST bodies.
- **[`Learning/django-url-routing.md`](django-url-routing.md)** — which URL handles `/accounts/login/`.

---

## What a Django Form does

A **`forms.Form`** (or **`forms.ModelForm`**) describes:

1. **Which fields** exist (`username`, `password`, …).
2. **How to validate** them (`clean_<field>` methods, validators).
3. **How to render** them as HTML widgets (`CharField` → `<input type="text">`, etc.).

Baby translation:

> **The form is the bouncer + clipboard at the door.**  
> It decides “allowed / not allowed” and fills in the blanks safely.

---

## Bound vs unbound forms

- **Unbound**: built from GET request or empty → shows empty fields (login page first visit).
- **Bound**: built from `request.POST` → Django validates; `.errors` fills if invalid.

```python
form = MyForm(request.POST)  # bound
form.is_valid()              # runs validation
```

---

## Authentication login form

Django ships **`AuthenticationForm`** (`django.contrib.auth.forms`).  
Class-based **`LoginView`** uses it by default to validate username/password against the user database.

This project subclasses it as **`BootstrapAuthenticationForm`** to add Bootstrap CSS classes (`form-control`, `is-invalid`) so templates look consistent without extra markup hacks.

---

## Hooking a custom form to `LoginView`

In [`DigicelAssessment/accounts/views.py`](../DigicelAssessment/accounts/views.py), **`RoleAwareLoginView`** sets:

```python
authentication_form = BootstrapAuthenticationForm
```

That tells Django: “when rendering/processing login, use **this** form class.”

---

## Rendering forms in templates

Common patterns:

- **`{{ form.as_p }}`** — quick but less layout control.
- **Loop `{% for field in form %}`** — full control; this project uses this in `login.html`.
- **`{% csrf_token %}`** — required for POST forms (CSRF protection).

Field errors: **`field.errors`** after a failed POST.

Non-field errors (e.g. “inactive account”): **`form.non_field_errors`**.

---

## Quick checklist when adding a new form

1. Define a **`forms.Form`** (or **`ModelForm`**) in `forms.py`.
2. Instantiate it in the view: **`GET`** → empty form; **`POST`** → `Form(request.POST)`.
3. If **`form.is_valid()`**, save or process **`form.cleaned_data`**.
4. **`render`** template with **`{"form": form}`**.
5. Template: show **`non_field_errors`**, loop fields, **`csrf_token`**.

---

## Where to read next in this repo

| Piece | File |
|-------|------|
| Bootstrap-styled login fields | [`DigicelAssessment/accounts/forms.py`](../DigicelAssessment/accounts/forms.py) |
| Login template loop | [`DigicelAssessment/templates/accounts/login.html`](../DigicelAssessment/templates/accounts/login.html) |
| View wiring | [`DigicelAssessment/accounts/views.py`](../DigicelAssessment/accounts/views.py) (`RoleAwareLoginView`) |
