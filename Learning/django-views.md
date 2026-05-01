# How Django views work (concept + this project)

This note explains **views**: the Python functions or classes that turn an incoming web **request** into an outgoing **response**.

Examples reference [`DigicelAssessment/accounts/views.py`](../DigicelAssessment/accounts/views.py).

Related topics:

- **[`Learning/django-url-routing.md`](django-url-routing.md)** — how URLs choose which view runs.
- **[`Learning/django-models-and-packages.md`](django-models-and-packages.md)** — models vs apps.

---

## Request → view → response (baby terms)

1. The browser asks Django for a URL path like `/customer/`.
2. Django’s URL router picks a **view**.
3. The view runs Python code using the **`request`** object (cookies, session, logged-in user, form POST data).
4. The view returns an **`HttpResponse`** (often HTML), or a **redirect**.

Baby translation:

> **URLs are addresses; views are the workers at each desk.**

---

## What `request` contains (mental checklist)

Common useful attributes:

- **`request.method`**: `"GET"`, `"POST"`, etc.
- **`request.user`**: who is logged in (or anonymous).
- **`request.GET` / `request.POST`**: query/form fields.
- **`request.session`**: server-side remembered data for this visitor.

Views almost never construct raw sockets—Django hands them a filled-in **`HttpRequest`**.

---

## Function views vs class-based views

### Function views

A plain Python function:

```python
def customer_home(request):
    ...
```

Easy to read; often paired with decorators like `@login_required` or your `@role_required(...)`.

### Class-based views (CBVs)

A class with methods like `.get()`, `.post()`, `.dispatch()`:

```python
class RoleAwareLoginView(LoginView):
    ...
```

Django ships CBVs for common patterns (`LoginView`, `LogoutView`, list/detail CRUD helpers).

Baby translation:

- Function view = **one worker does everything**.
- CBV = **a small machine with labeled buttons** (`get`, `post`) Django calls automatically.

This project uses **both**:

- **`RoleAwareLoginView`** subclasses Django’s **`LoginView`** (built-in login machinery).
- **`RoleLogoutView`** subclasses **`LogoutView`**.
- **`role_home_redirect`**, **`customer_home`**, etc. are **functions**.

---

## Typical response types

### HTML page (`render`)

```python
return render(request, "accounts/role_home.html", {"heading": "Customer home"})
```

Django merges a template + context dict into HTML.

### Redirect (`redirect`)

```python
return redirect(reverse("accounts:customer_home"))
```

Tells the browser “go somewhere else” (often after login).

### Errors / blocks (`HttpResponseForbidden`)

```python
return HttpResponseForbidden("User profile is missing.")
```

Returns HTTP **403** with a plain message.

Baby translation:

- **render** = “here’s a webpage.”
- **redirect** = “go to another URL.”
- **403** = “stop; you’re not allowed.”

---

## How routing connects to views

[`DigicelAssessment/accounts/urls.py`](../DigicelAssessment/accounts/urls.py) wires paths to views:

```python
path("customer/", views.customer_home, name="customer_home")
```

So `/customer/` calls `customer_home`.

---

## Patterns used in this project

### 1) Role-aware landing redirect (`/`)

**Goal**: send logged-in users to the correct **role home**.

[`role_home_redirect`](../DigicelAssessment/accounts/views.py) checks authentication + profile role and **`redirect`s**.

### 2) Login with safe “next” handling (`RoleAwareLoginView`)

**Goal**:

- Let users continue where they intended (`?next=/somewhere`) **only if it’s safe** (same-site rules).
- Otherwise fall back to role-specific destinations via **`get_success_url()`**.

That prevents **open redirects** (attackers tricking your site into redirecting users to malicious URLs).

### 3) POST-only logout (`RoleLogoutView`)

**Goal**: logout should come from a **form POST** with CSRF protection.

Baby translation: logout isn’t a casual link-click GET by default—it's an intentional button submit.

### 4) Protected placeholder pages (`customer_home`, `agent_home`, `admin_home`)

These views are wrapped by **`@role_required(...)`** from [`accounts/decorators.py`](../DigicelAssessment/accounts/decorators.py).

Baby translation:

> Before showing “Customer home”, Django checks **two IDs**:

1. logged in?

2. badge says **customer**?

If checks fail, the decorator stops early (redirect login / 403).

---

## Views vs templates vs static assets

| Piece | Responsibility |
|---|---|
| **View** | Decide what happens for this URL + build response |
| **Template** | Mostly HTML layout + placeholders (`{{ heading }}`) |
| **Static/CSS/JS** | Styling/scripts (often Phase 3+) |

Phase 2 intentionally keeps templates minimal; Phase 3 adds richer Bootstrap layouts.

---

## Practical debugging checklist

- **Wrong page renders**: URL pattern points at the wrong view.
- **Always redirects to login**: user not authenticated or `@role_required` firing.
- **403 Forbidden**: missing profile row or wrong role.
- **Login loops**: conflicting redirects (`LOGIN_URL`, `LOGIN_REDIRECT_URL`, bad `next`).
- **POST fails**: CSRF token missing in template forms (`{% csrf_token %}`).

---

## Tiny diagram

```text
HTTP GET /customer/
      |
      v
urls.py picks views.customer_home
      |
      v
@role_required(CUSTOMER) checks permissions
      |
      v
render(...) returns HTML HttpResponse
```
