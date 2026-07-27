# Authentication & Subscription Platform — Truetalk

## Overview

Truetalk uses a **phone-first, OTP-less** authentication model. Users are identified by their MTN Nigeria phone number (MSISDN). The system queries **IntelliHQ** to determine whether the caller has an active subscription. If yes, they are signed in automatically. If not, they are given a link to subscribe.

This document covers every component with **complete code blocks** so developers can understand, debug, or reimplement the flow.

---

## Architecture

```
┌──────────┐      ┌─────────────┐      ┌──────────────┐      ┌───────────┐
│  Browser  │ ──► │  Django App  │ ──► │  IntelliHQ   │ ──► │  MTN DCB  │
│ (User)    │ ◄── │ (truetalk)   │ ◄── │  (API)       │ ◄── │ (Telco)   │
└──────────┘      └──────┬──────┘      └──────────────┘      └───────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │  PostgreSQL  │
                  │ (Local DB)   │
                  └──────────────┘
```

---

## 1. Core models (`ums/models.py`)

### `UserProfile`

| Field | Type | Purpose |
|-------|------|---------|
| `phone` | `CharField` | MSISDN in international format (`2348012345678`) |
| `first_name`, `last_name` | `CharField` | Optional user info |
| `sub_status` | `CharField` | One of `active`, `inactive`, `no_sub` |
| `test_phase` | `CharField` | A/B test segmentation |
| `traffic_source` | `CharField` | Campaign partner attribution |
| `created_at` | `DateTimeField` | When the profile was first seen |

### `UserSubscribtion`

| Field | Type | Purpose |
|-------|------|---------|
| `user` | `FK → UserProfile` | One-to-one with the user |
| `sub_active` | `BooleanField` | Whether the subscription is currently active |
| `starts_date` / `ends_date` | `DateTimeField` | Subscription validity window |
| `auto_renewal` | `BooleanField` | Whether MTN will auto-renew |
| `first_sub` / `renewal_sub` | `BooleanField` | Subscription lifecycle flags |
| `traffic_source` | `CharField` | Source attribution |

### `DataSync` / `CallbackNotification`

- `DataSync` — Records every subscription event pushed by IntelliHQ (new subs, renewals, unsubs).
- `CallbackNotification` — Raw telco provider callback payloads stored for auditing.

---

## 2. Utility functions (`ums/utils.py`)

### MSISDN resolution & normalization

```python
def resolve_msisdn_from_request(request) -> str | None:
    """
    Resolve the caller's MSISDN by priority:
      1. Msisdn request header (telco gateway)
      2. 'sub_msisdn' signed cookie (phone-login users)
    Returns a normalized 234-prefixed phone string or None.
    """
    if "Msisdn" in request.headers:
        raw = request.headers["Msisdn"]
        return _normalize_msisdn(raw)

    raw = request.get_signed_cookie("sub_msisdn", default=None, salt="ums")
    if raw:
        return _normalize_msisdn(raw)

    return None


def _normalize_msisdn(phone: str) -> str:
    """Converts 08012345678 → 2348012345678. Leaves 234... unchanged."""
    phone = phone.strip()
    if phone.startswith("0") and len(phone) == 11:
        return "234" + phone[1:]
    return phone
```

### Cookie helper

```python
COOKIE_SALT = "ums"
COOKIE_MAX_AGE = 86400 * 1  # 1 day

def set_auth_cookies(response, msisdn, sub_active=False):
    """Set identity and subscription-status cookies on any response."""
    response.set_signed_cookie("sub_msisdn", msisdn,
        salt=COOKIE_SALT, max_age=COOKIE_MAX_AGE,
        httponly=True, samesite="Lax")
    response.set_signed_cookie("sub_active", "1" if sub_active else "0",
        salt=COOKIE_SALT, max_age=COOKIE_MAX_AGE,
        httponly=True, samesite="Lax")
    return response
```

### IntelliHQ API wrapper

```python
INTELLI_SERVICE_ID = 28

def _intellihq_check_subscriber(msisdn: str) -> dict:
    """
    GET /api/v1/service/{id}/subscription/status/?msisdn=...
    Returns subscription status from IntelliHQ.
    """
    url = (f"https://api.intellihq.net/api/v1/service/"
           f"{INTELLI_SERVICE_ID}/subscription/status/")
    response = http_requests.get(
        url, params={"msisdn": msisdn},
        headers={"Content-Type": "application/json"},
        timeout=15)
    data = response.json()
    response.raise_for_status()
    return data
```

### Subscription sync

```python
def _sync_subscription_from_intellihq(msisdn: str, data: dict) -> None:
    """Sync IntelliHQ subscription data into local UserSubscribtion."""
    from django.utils.dateparse import parse_datetime

    has_active = data.get("has_active_subscription", False)
    active_sub = data.get("active_subscription") or {}

    profile, _ = UserProfile.objects.get_or_create(phone=msisdn)
    sub, _ = UserSubscribtion.objects.get_or_create(user=profile)

    sub.sub_active = has_active
    if active_sub:
        sub.auto_renewal = active_sub.get("auto_renewal", False)
        sub.starts_date = parse_datetime(active_sub.get("starts_date"))
        sub.ends_date = parse_datetime(active_sub.get("ends_date"))
    sub.save()

    profile.sub_status = "active" if has_active else "inactive"
    profile.save(update_fields=["sub_status"])
```

---

## 3. IntelliHQ API contract

All calls go to `https://api.intellihq.net/api/v1/service/{service_id}/…`

### `fetch-subscription-status` (primary)

```
GET /api/v1/service/28/subscription/status/?msisdn=2348031234567
```

**Active subscription response:**

```json
{
  "success": true,
  "data": {
    "service_id": 28,
    "msisdn": "2348031234567",
    "has_active_subscription": true,
    "active_subscription": {
      "auto_renewal": true,
      "starts_date": "2026-06-01T00:00:00Z",
      "ends_date": "2026-06-08T00:00:00Z"
    },
    "client_action": null
  }
}
```

**No subscription response:**

```json
{
  "success": true,
  "data": {
    "service_id": 28,
    "msisdn": "2348031234567",
    "has_active_subscription": false,
    "active_subscription": null,
    "client_action": [
      {"action": "prompt", "instruction": "Send TTM keyword to 2OO71"},
      {"action": "redirect", "redirection_url": "https://checkout.mtn-ng..."}
    ]
  }
}
```

| Field | Type | Notes |
|-------|------|-------|
| `data.has_active_subscription` | boolean | Whether the user currently has an active subscription |
| `data.active_subscription` | object \| null | **Nullable** |
| `data.client_action` | array \| null | **List** of action objects; **nullable** |
| `data.client_action[].action` | string | `"prompt"` or `"redirect"` |
| `data.client_action[].redirection_url` | string \| null | **Nullable** — the subscribe URL |

---

## 4. Phone Login view — complete code (`ums/views.py`)

```python
@never_cache
def phone_login(request):
    next_url = request.GET.get("next") or request.POST.get("next") or ""

    # ── STEP 0: Handle ?reset=1 (clear stored state) ──
    if request.method == "GET" and request.GET.get("reset"):
        request.session.pop("sub_redirect_url", None)
        request.session.pop("saved_phone", None)

    # ── STEP 1: GET — returning user with saved redirect? ──
    if request.method == "GET":
        msisdn = resolve_msisdn_from_request(request)
        saved_redirect = request.session.get("sub_redirect_url")
        if msisdn and saved_redirect:
            return render(request, "ums/phone_login.html", {
                "no_subscription": True,
                "msisdn": msisdn,
                "redirect_url": saved_redirect,
                "next": next_url,
            })

    # ── STEP 2: POST — form submitted ──
    if request.method == "POST":
        phone = request.POST.get("phone", "").strip()
        if not phone:
            return render(request, "ums/phone_login.html",
                          {"error": "Please enter a phone number.", "next": next_url})

        msisdn = _normalize_msisdn(phone)
        request.session["saved_phone"] = msisdn
        UserProfile.objects.get_or_create(phone=msisdn)

        # 2a: Call IntelliHQ
        try:
            result = _intellihq_check_subscriber(msisdn)
        except Exception as exc:
            logger.error(f"[IntelliHQ] check-subscriber failed for {msisdn}: {exc}")
            return set_auth_cookies(
                render(request, "ums/phone_login.html",
                       {"error": "Service unavailable. Please try again.",
                        "next": next_url}),
                msisdn)

        # 2b: Normalise list → dict
        if isinstance(result, list):
            result = result[0] if result else {}
        if not isinstance(result, dict) or not result.get("success"):
            return set_auth_cookies(
                render(request, "ums/phone_login.html",
                       {"error": result.get("message",
                           "Unable to verify subscription. Please try again."),
                        "next": next_url}),
                msisdn)

        # 2c: Parse subscription data
        sub_data = result.get("data") or {}
        if isinstance(sub_data, list):
            sub_data = sub_data[0] if sub_data else {}
        has_active = sub_data.get("has_active_subscription", False)

        # ── STEP 3: SUBSCRIBED ──
        if has_active:
            _sync_subscription_from_intellihq(msisdn, sub_data)
            request.session.pop("sub_redirect_url", None)
            redirect_to = next_url or "content:home"
            response = redirect(redirect_to)
            return set_auth_cookies(response, msisdn, sub_active=True)

        # No active subscription — show subscribe prompt
        redirect_url = ""
        client_actions = sub_data.get("client_action") or []
        if isinstance(client_actions, list):
            for action in client_actions:
                if isinstance(action, dict) and action.get("action") == "redirect":
                    redirect_url = action.get("redirection_url", "")
                    break
        elif isinstance(client_actions, dict):
            redirect_url = client_actions.get("redirection_url", "")

        if redirect_url:
            request.session["sub_redirect_url"] = redirect_url

        return set_auth_cookies(
            render(request, "ums/phone_login.html", {
                "no_subscription": True,
                "msisdn": msisdn,
                "redirect_url": redirect_url,
                "next": next_url,
            }),
            msisdn)

    # ── STEP 5: Fresh GET — show the form ──
    return render(request, "ums/phone_login.html", {
        "saved_phone": request.session.pop("saved_phone", None),
        "next": next_url,
    })
```

### Decision tree

```
GET /phone-login/
  ├── ?reset=1 → clear session, show form
  ├── has cookie + saved_redirect? → show subscribe prompt (no form)
  └── else → show phone form

POST /phone-login/
  ├── normalize MSISDN → save to session → ensure UserProfile
  ├── call IntelliHQ GET /subscription/status/?msisdn=...
  │     ├── exception → render form with error + set sub_msisdn cookie
  │     └── success=false → render form with error + set sub_msisdn cookie
  └── success=true
        ├── has_active_subscription=true
        │     ├── sync local DB
        │     ├── set sub_msisdn + sub_active=1 cookies
        │     └── redirect to next_url or home
        └── has_active_subscription=false
              ├── extract redirect_url from client_action list
              ├── save to session
              ├── set sub_msisdn cookie
              └── render subscribe prompt
```

---

## 5. `@allowed_users` decorator (`ums/decorators.py`)

Uses a **fast-path cookie check** to avoid unnecessary DB queries.

```python
from urllib.parse import quote
from django.shortcuts import redirect
from .models import UserProfile, UserSubscribtion
from .utils import resolve_msisdn_from_request, COOKIE_SALT


def allowed_users(function):
    def wrapper_func(request, *args, **kwargs):
        msisdn = resolve_msisdn_from_request(request)

        if not msisdn:
            next_url = quote(request.get_full_path())
            return redirect(f"{redirect('ums:phone_login').url}?next={next_url}")

        # ⚡ Fast path: check signed sub_active cookie first
        sub_active_cookie = request.get_signed_cookie(
            "sub_active", default=None, salt=COOKIE_SALT)
        if sub_active_cookie == "1":
            return function(request, *args, **kwargs)

        # Slow path: verify against local DB
        theUser, _ = UserProfile.objects.get_or_create(phone=msisdn)
        sub_qs = UserSubscribtion.objects.filter(user=theUser)
        if sub_qs.exists() and sub_qs.first().sub_active:
            return function(request, *args, **kwargs)

        # Not subscribed → re-check with IntelliHQ via phone_login
        next_url = quote(request.get_full_path())
        return redirect(f"{redirect('ums:phone_login').url}?next={next_url}")

    wrapper_func.__doc__ = function.__doc__
    wrapper_func.__name__ = function.__name__
    return wrapper_func
```

**Flow:**

1. Resolve MSISDN (header → cookie)
2. No MSISDN → `phone_login?next=/original/path/`
3. **Fast path**: `sub_active` cookie = `"1"` → **zero DB queries**, allow
4. **Slow path**: check DB → if active, allow
5. Not active → `phone_login?next=/original/path/`

### Usage in content views

```python
from ums.decorators import allowed_users

@allowed_users
def content_detail(request, slug=None):
    # ... episode playback ...
```

---

## 6. Context processor (`content/context_processor.py`)

Makes MSISDN available in all templates (used by `_header.html`).

```python
from ums.utils import resolve_msisdn_from_request

def fetch_msisdn(request):
    msisdn = resolve_msisdn_from_request(request)
    return {"msisdn": msisdn or "Start Watching"}
```

---

## 7. Template (`content/templates/ums/phone_login.html`)

Server-rendered dual-state page (no JavaScript fetch):

```django
{% extends 'content/base.html' %}
{% load static %}

{% block head_title %}
    {% if no_subscription %}No Active Subscription{% else %}Phone Login{% endif %}
{% endblock head_title %}

{% block content %}
    <div class="breadcumb-wrapper" data-bg-src="...">
        <div class="container">
            <div class="breadcumb-content">
                <h1 class="breadcumb-title">
                    {% if no_subscription %}No Active Subscription{% else %}Sign In{% endif %}
                </h1>
            </div>
        </div>
    </div>

    <section class="space-top space-extra-bottom">
        <div class="container">
            <div class="row justify-content-center">
                <div class="col-lg-6 col-md-8">
                    <div class="vs-box p-4 p-lg-5">

                        {% if no_subscription %}
                            {# ── Subscribe prompt ── #}
                            <h2 class="sec-title h3">No Active Subscription Found</h2>
                            <p class="fs-sm tcn-700">
                                <strong>{{ msisdn }}</strong> does not have an active subscription.
                            </p>
                            {% if redirect_url %}
                                <a href="{{ redirect_url }}" class="vs-btn w-100">
                                    <i class="fas fa-plus-circle me-2"></i> Subscribe Now
                                </a>
                            {% endif %}
                            <a href="{% url 'ums:phone_login' %}?reset=1">
                                Try a different number
                            </a>

                        {% else %}
                            {# ── Phone input form ── #}
                            <h2 class="sec-title h3">Check your subscription</h2>
                            {% if error %}
                                <div class="alert alert-danger">{{ error }}</div>
                            {% endif %}
                            <form method="post" action="{% url 'ums:phone_login' %}">
                                {% csrf_token %}
                                {% if next %}
                                    <input type="hidden" name="next" value="{{ next }}">
                                {% endif %}
                                <input type="tel" name="phone" required
                                       value="{{ saved_phone|default:'' }}"
                                       placeholder="e.g. 08031234567">
                                <button type="submit" class="vs-btn w-100">
                                    Check Subscription
                                </button>
                            </form>
                        {% endif %}

                    </div>
                </div>
            </div>
        </div>
    </section>
{% endblock content %}
```

Context variables:

| Variable | Type | When present |
|----------|------|-------------|
| `no_subscription` | bool | `True` only when user is not subscribed |
| `msisdn` | str | The normalized phone number |
| `redirect_url` | str \| empty | The IntelliHQ subscribe URL |
| `error` | str \| absent | Error message from API or validation |
| `saved_phone` | str \| absent | Pre-fill value from previous POST |
| `next` | str \| absent | URL to redirect to after successful login |

---

## 8. Webhook callbacks (server-to-server)

### `intelli_datasync` → `POST /ums/intelli-datasync/`

```python
@require_POST
@csrf_exempt
def intelli_datasync(request):
    the_data = json.loads(request.body)
    tasks.process_datasync.delay(the_data)
    return JsonResponse({"status": 200, "message": "ok"})
```

### `callback_notification` → `POST /ums/callback_notification/`

```python
@require_POST
@csrf_exempt
def callback_notification(request):
    data = json.loads(request.body)
    CallbackNotification.objects.create(
        msisdn=data.get("msisdn"),
        activation=data.get("activation"),
        product_id=data.get("productId"),
        description=data.get("description"),
        timestamp=data.get("timestamp"),
        trx_id=data.get("trxID"),
        sequence_no=data.get("sequenceNo"),
        raw_payload=data,
    )
    return JsonResponse({"status": 200, "message": "Saved"})
```

---

## 9. Celery task `process_datasync` (`ums/tasks.py`)

```python
@shared_task
def process_datasync(payload):
    """Process subscription webhook payload from IntelliHQ."""
    sync = utils.handle_datasync_payload(payload)
    phone = payload["details"]["phone"]
    profile, _ = UserProfile.objects.get_or_create(phone=phone)
    sub, _ = UserSubscribtion.objects.get_or_create(user=profile)
    sub.sub_active = (payload["type"] != "UNSUBSCRIPTION_NOTIFICATION")
    sub.save()
    profile.sub_status = "active" if sub.sub_active else "inactive"
    profile.save(update_fields=["sub_status"])
```

---

## 10. URL reference

| URL | View name | Method | Auth |
|-----|-----------|--------|------|
| `/ums/phone-login/` | `ums:phone_login` | GET, POST | No |
| `/ums/subscribe/` | `ums:subscribe` | GET | No |
| `/ums/onboarding/` | `ums:onboarding` | GET | No |
| `/ums/inactive_account/` | `ums:inactive_account` | GET | No |
| `/ums/awaiting_response/` | `ums:awaiting_response` | GET | No |
| `/ums/check_sub_status/` | `ums:check_sub_status` | GET | Header |
| `/ums/intelli-datasync/` | `ums:intelli-datasync` | POST | CSRF exempt |
| `/ums/callback_notification/` | `ums:callback_notification` | POST | CSRF exempt |

---

## 11. Environment & configuration

| Variable | Value | Location |
|----------|-------|----------|
| `INTELLI_SERVICE_ID` | `28` | `ums/utils.py` |
| `COOKIE_SALT` | `"ums"` | `ums/utils.py` |
| `COOKIE_MAX_AGE` | `86400` (1 day) | `ums/utils.py` |
| IntelliHQ base | `https://api.intellihq.net` | — |

---

## 12. Best practices

### Phone number handling
- Always normalize via `_normalize_msisdn()` before API calls.
- Save to session immediately so user doesn't retype on error.

### API response validation
- Check both HTTP status and `response.body.success`.
- Normalise list responses:

  ```python
  if isinstance(result, list):
      result = result[0] if result else {}
  ```

### `client_action` is an array
```python
redirect_url = ""
for action in (sub_data.get("client_action") or []):
    if isinstance(action, dict) and action.get("action") == "redirect":
        redirect_url = action.get("redirection_url", "")
        break
```

### Nullable fields
- `active_subscription` → use `.get("active_subscription") or {}`
- `client_action` → iterate safely with `or []`
- `redirection_url` → provide fallback UI

### Cookie strategy
- `sub_msisdn` (signed) — set on **every** POST response, even errors. Identifies the user.
- `sub_active` (signed, `"1"`/`"0"`) — set only when IntelliHQ confirms active sub. Enables fast-path in `@allowed_users`.

### Content protection
- Use `@allowed_users` decorator.
- Fast path: `sub_active` cookie → allow.
- Slow path: DB check → allow or redirect to `phone_login?next=...`.

---

## 13. Troubleshooting

| Symptom | Likely cause |
|---------|-------------|
| `'list' object has no attribute 'get'` | API returned a list; missing `isinstance(result, list)` normalisation |
| `Expecting value: line 2 column 1` | `response.json()` called twice on the same response object |
| Login → subscribe → login loop | `sub_active` cookie not set, or stale after subscription |
| Cookie not persisting | Must call `set_signed_cookie` on the response before returning it |
| `sub_active` cookie ignored | Signed cookie salt must match (`"ums"`) |

