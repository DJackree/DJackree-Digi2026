# How Django URL routing works (this project)

This note explains **routing**: how a browser URL like `http://localhost:8000/customer/` ends up running a specific Python **view**.

## The big picture

1. Django receives an HTTP request with a **path** (for example `/customer/`).
2. Django walks the **`urlpatterns`** list (rules) **from top to bottom**.
3. The **first matching rule** wins.
4. That rule tells Django **which view function/class** should handle the request.

Think of `urlpatterns` as an ordered checklist of instructions: “If the URL starts like this, go here.”

## Where routing lives in this repo

This project uses two layers:

1. **Project URLs**: [`DigicelAssessment/config/urls.py`](../DigicelAssessment/config/urls.py)
2. **App URLs**: [`DigicelAssessment/accounts/urls.py`](../DigicelAssessment/accounts/urls.py)

The project file imports rules from app files using `include(...)`.

## `path(...)` basics

Common shape:

```python
path("some/path/", some_view)
```

- **`"some/path/"`**: the URL segment Django matches **after** any prefix added by parent includes.
- **`some_view`**: the Python callable that builds the HTTP response.

Trailing slashes matter by default (`APPEND_SLASH` redirects `/customer` → `/customer/` when configured).

## `include(...)` lets apps own their URLs

Instead of dumping every route into `config/urls.py`, Django lets each app declare routes:

```python
path("", include("accounts.urls"))
```

That means:

> “Delegate matching to `accounts.urls` using **no extra prefix**.”

So routes declared inside `accounts/urls.py` become **full site paths from the domain**.

### Empty prefix (`""`) vs non-empty prefix

**Empty prefix example (what this project does)**

Root:

```python
path("", include("accounts.urls"))
```

App (`accounts/urls.py`) contains:

```python
path("customer/", views.customer_home)
```

Final browser URL:

```text
http://localhost:8000/customer/
```

**Non-empty prefix example (hypothetical)**

Root:

```python
path("portal/", include("accounts.urls"))
```

Same app route `"customer/"` would become:

```text
http://localhost:8000/portal/customer/
```

Baby translation:

- Empty prefix = **no extra folder name** inserted before app routes.
- Non-empty prefix = **everything in that app moves under `/portal/`**.

## Namespaces and URL names (`name=`)

Routes can have names:

```python
path("accounts/login/", views.RoleAwareLoginView.as_view(), name="login")
```

With `app_name = "accounts"` in `accounts/urls.py`, Django refers to this route as:

```text
accounts:login
```

Why names matter:

- Templates can generate URLs safely with `{% url 'accounts:login' %}`.
- Settings like `LOGIN_URL = "accounts:login"` point auth redirects at the named route instead of hardcoding `/accounts/login/`.

If you rename the actual path later, **named URLs reduce breakage** because references update centrally.

## Admin routing is separate

In `config/urls.py`:

```python
path("admin/", admin.site.urls)
```

Anything under `/admin/` is handled by Django’s admin site.

Order tip: put **more specific** routes before overly broad routes if they could overlap.

## Mental model diagram

```text
Browser URL path
      |
      v
config/urlpatterns (project)
      |
      +--> /admin/*  --> Django admin
      |
      +--> include("accounts.urls") with prefix ""
               |
               v
           accounts/urlpatterns (app)
               |
               +--> /accounts/login/
               +--> /customer/
               +--> ...
```

## Practical debugging checklist

- **404**: no matching pattern (check trailing slash, typo, wrong prefix).
- **Wrong view**: pattern matched earlier than you expected (move/adjust pattern order).
- **Redirect loops**: login/settings redirects conflicting (`LOGIN_URL`, `LOGIN_REDIRECT_URL`).
- **403 on forms**: CSRF/`CSRF_TRUSTED_ORIGINS`/HTTPS mismatches for POST requests.

## Related settings (auth redirects)

These do **not** define routes themselves, but they **reference named routes**:

- `LOGIN_URL`
- `LOGIN_REDIRECT_URL`
- `LOGOUT_REDIRECT_URL`

See [`DigicelAssessment/config/settings.py`](../DigicelAssessment/config/settings.py).
