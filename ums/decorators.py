from django.http import HttpResponse
from django.shortcuts import redirect
from .models import UserProfile, UserSubscribtion


def allowed_users(function):
    def wrapper_func(request, *args, **kwargs):
        # fetch request body
        if "Msisdn" in request.headers:
            msisdn = request.headers["Msisdn"]
            if msisdn.startswith("0") and len(msisdn) == 11:
                msisdn = msisdn.replace("0", "234", 1)

            # check or create profile
            theUser, created = UserProfile.objects.get_or_create(phone=msisdn)
            fetchSubscribtion = UserSubscribtion.objects.filter(user=theUser)
            if fetchSubscribtion.exists():
                theSub = fetchSubscribtion.first()
                if theSub.sub_active == True:
                    return function(request, *args, **kwargs)
                else:
                    return redirect("users:subscribe")
            else:
                return redirect("users:subscribe")
        else:
            # redirect to subscribe page
            return redirect("users:subscribe")

    wrapper_func.__doc__ = function.__doc__
    wrapper_func.__name__ = function.__name__
    return wrapper_func
