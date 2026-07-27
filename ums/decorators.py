from urllib.parse import quote

from django.shortcuts import redirect
from django.urls import reverse

from .models import UserProfile, UserSubscribtion
from .utils import COOKIE_SALT, resolve_msisdn_from_request


def _redirect_to_phone_login(request):
    next_url = quote(request.get_full_path())
    return redirect(f"{reverse('users:phone_login')}?next={next_url}")


def allowed_users(function):
    def wrapper_func(request, *args, **kwargs):
        msisdn = resolve_msisdn_from_request(request)

        if not msisdn:
            return _redirect_to_phone_login(request)

        # Fast path: check signed sub_active cookie first, no DB query
        sub_active_cookie = request.get_signed_cookie(
            "sub_active", default=None, salt=COOKIE_SALT
        )
        if sub_active_cookie == "1":
            return function(request, *args, **kwargs)

        # Slow path: verify against local DB
        theUser, _ = UserProfile.objects.get_or_create(phone=msisdn)
        sub_qs = UserSubscribtion.objects.filter(user=theUser)
        if sub_qs.exists() and sub_qs.first().sub_active:
            return function(request, *args, **kwargs)

        return _redirect_to_phone_login(request)

    wrapper_func.__doc__ = function.__doc__
    wrapper_func.__name__ = function.__name__
    return wrapper_func
