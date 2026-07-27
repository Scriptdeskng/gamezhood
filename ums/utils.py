import logging

import requests
from django.utils.dateparse import parse_datetime

from .models import UserProfile, UserSubscribtion

logger = logging.getLogger(__name__)

COOKIE_SALT = "ums"
COOKIE_MAX_AGE = 86400  # 1 day
INTELLI_SERVICE_ID = 8


def _normalize_msisdn(phone):
    """Converts 08012345678 -> 2348012345678. Leaves 234... unchanged."""
    phone = phone.strip()
    if phone.startswith("0") and len(phone) == 11:
        return "234" + phone[1:]
    return phone


def resolve_msisdn_from_request(request):
    """
    Resolve the caller's MSISDN by priority:
      1. Msisdn request header (telco gateway)
      2. 'sub_msisdn' signed cookie (phone-login users)
    """
    if "Msisdn" in request.headers:
        return _normalize_msisdn(request.headers["Msisdn"])

    raw = request.get_signed_cookie("sub_msisdn", default=None, salt=COOKIE_SALT)
    if raw:
        return _normalize_msisdn(raw)

    return None


def set_auth_cookies(response, msisdn, sub_active=False):
    """Set identity and subscription-status cookies on any response."""
    response.set_signed_cookie(
        "sub_msisdn",
        msisdn,
        salt=COOKIE_SALT,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax",
    )
    response.set_signed_cookie(
        "sub_active",
        "1" if sub_active else "0",
        salt=COOKIE_SALT,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax",
    )
    return response


def _intellihq_check_subscriber(msisdn):
    """GET /api/v1/service/{id}/subscription/status/?msisdn=... from IntelliHQ."""
    url = (
        f"https://api.intellihq.net/api/v1/service/"
        f"{INTELLI_SERVICE_ID}/subscription/status/"
    )
    response = requests.get(
        url,
        params={"msisdn": msisdn},
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def _sync_subscription_from_intellihq(msisdn, data):
    """Sync IntelliHQ subscription data into local UserSubscribtion."""
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
