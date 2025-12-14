from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.shortcuts import HttpResponse, redirect, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt


from django.db.models import Sum, Q
from celery.result import AsyncResult
from config.celery import app as celery_app

from datetime import datetime

from .models import *

# from .subscriptionManager import mtnSubscribe, mtnUnSubscribe
import json
from . import choices


from django.utils.crypto import get_random_string

from .subscriptionManager import HML

from . import tasks

import logging


logger = logging.getLogger(__name__)


def subscribe(request):
    try:
        res = get_random_string(length=48)
        traffic_source = "Organic Search"
        redirect_url = f"http://mtn-nigeria-prod.mfilterit.org/sid/234102200008007?origin_banner=1&trxId={res}&trfsrc={traffic_source}"
        return redirect(redirect_url)
    except Exception as ex:
        print(ex)
        return redirect("core:home")

    # check subscription status
    ###########


######### Unsubscribe ###########


def cancelSubscribtion(request):
    if "Msisdn" in request.headers:
        msisdn = request.headers["Msisdn"]
        # get user msisdn
        client = HML()

        checkNetwork = client.checkNetwork(msisdn)
        if checkNetwork == "AIRTEL":
            unSub = client.unSubscribe(msisdn, choices.Telco.AIRTEL.value)
        # elif checkNetwork == "MTN":
        else:
            unSub = client.unSubscribe(msisdn, choices.Telco.MTN.value)

        if unSub != False:
            print("Un-Subscribtion Successfull")
            return redirect("core:home")
        else:
            print("Subscribtion UnSuccessfull")
            return redirect("core:home")
    else:
        return redirect("users:onboarding")


def awaiting_response(request):
    template = "users/awaiting_response.html"
    return render(request, template)


def onboarding(request):
    template = "users/subscribe_page.html"

    context = {"page_title": "Subscribe"}

    return render(request, template, context)


def inactive_account(request):
    template = "users/inactive_account.html"

    context = {}
    return render(request, template, context)


# DATA SYNC
@require_POST
@csrf_exempt
def data_sync(request):
    print("Receiving from HML datasync")

    the_data = json.loads(request.body)
    print(the_data)

    try:
        new_sync_data = DataSync.objects.create(
            type=the_data["type"],
            telco=the_data["telco"],
            product_id=the_data["product"]["id"],
            product_name=the_data["product"]["name"],
            product_not_type=the_data["product"]["type"],
            product_sub_type=the_data["product"]["subscription_type"],
            phone=the_data["details"]["phone"],
            telco_ref=the_data["details"]["telco_ref"],
        )
        if the_data["details"]["amount"]:
            new_sync_data.amount = int(the_data["details"]["amount"]) / 100
        if the_data["details"]["channel"]:
            new_sync_data.channel = the_data["details"]["channel"]
        if the_data["details"]["date"]:
            new_sync_data.sub_date = the_data["details"]["date"]
        if the_data["details"]["auto_renewal"]:
            new_sync_data.auto_renewal = the_data["details"]["auto_renewal"]
        if the_data["details"]["expiry"]:
            new_sync_data.sub_expiry = the_data["details"]["expiry"]

        new_sync_data.save()
    except Exception as ex:
        print("saving datasync error", ex)
        pass

    try:
        if the_data["telco"] == "MTN":
            not_type = the_data[
                "type"
            ]  # UNSUBSCRIPTION_NOTIFICATION, SYNC_NOTIFICATION
            msisdn = the_data["details"]["phone"]
            # "%Y-%m-%dT%H:%M:%S.%fZ",

            prod_type = the_data["product"]["type"]
            # sub_type = the_data["product"]["subscription_type"]
            print("prod_type", prod_type)

            if msisdn.startswith("0") and len(msisdn) == 11:
                msisdn = msisdn.replace("0", "234", 1)

            # fetch user
            theUser, user_created = UserProfile.objects.get_or_create(phone=msisdn)
            userSub, sub_created = UserSubscribtion.objects.get_or_create(user=theUser)
            if not_type == "SYNC_NOTIFICATION":
                """
                b'{"type":"SYNC_NOTIFICATION","telco":"MTN","action":"NONE","shortcode":null,"product":{"id":70,"name":"Magic Box Daily","identity":"PD-16541987951000","type":"SUBSCRIPTION","subscription_type":"ONETIME_AND_RECURRING","status":"LIVE"},"details":{"phone":"2348130801443","amount":5000,"channel":"SecureD","date":"2023-01-07 08:57","expiry":"2023-01-08 08:57","auto_renewal":true,"telco_status_code":"0","telco_ref":"upstream_paid_f562330523f48921"}}'
                """

                start_date = the_data["details"]["date"]
                start_datetime = datetime.strptime(start_date, "%Y-%m-%d %H:%M")
                end_date = the_data["details"]["expiry"]
                end_datetime = datetime.strptime(end_date, "%Y-%m-%d %H:%M")

                sub_amount = 0.20

                userSub.sub_active = True
                userSub.starts_date = start_datetime
                userSub.ends_date = end_datetime

                try:
                    if not sub_created:
                        userSub.first_sub = True
                        if the_data["details"]["auto_renewal"] == True:
                            userSub.auto_renewal = True
                except:
                    pass
                userSub.save()

                theUser.sub_status = "active"
                theUser.save()

                return HttpResponse(200)

            elif not_type == "UNSUBSCRIPTION_NOTIFICATION":
                print("this is a unsubscribtion request")
                userSub.sub_active = False
                userSub.save()

                theUser.sub_status = "inactive"
                theUser.save()

                print("done with unsubscribtion")
                return HttpResponse(200)
            elif not_type == "RENEWAL_NOTIFICATION":
                """
                b'{"type":"RENEWAL_NOTIFICATION","telco":"MTN","action":"NONE","shortcode":null,"product":{"id":70,"name":"Magic Box Daily","identity":"PD-16541987951000","type":"SUBSCRIPTION","subscription_type":"ONETIME_AND_RECURRING","status":"LIVE"},"details":{"phone":"2347047344879","amount":5000,"channel":"system-renewal","date":"2023-01-07 08:58","expiry":"2023-01-08 08:58","auto_renewal":true,"telco_status_code":"0","telco_ref":"upstream_paid_2617724eebdbc3e8"}}'
                """
                start_date = the_data["details"]["date"]
                start_datetime = datetime.strptime(start_date, "%Y-%m-%d %H:%M")
                end_date = the_data["details"]["expiry"]
                end_datetime = datetime.strptime(end_date, "%Y-%m-%d %H:%M")

                userSub.sub_active = True

                userSub.starts_date = start_datetime
                userSub.ends_date = end_datetime

                try:
                    userSub.first_sub = False
                    userSub.renewal_sub = True
                    if the_data["details"]["auto_renewal"] == True:
                        userSub.auto_renewal = True
                except:
                    pass
                userSub.save()

                theUser.sub_status = "active"
                theUser.save()
                return HttpResponse(200)

            else:
                return HttpResponse(200)
        elif the_data["telco"] == "AIRTEL":
            pass
            # handle access
            return HttpResponse(200)
        else:
            return HttpResponse(200)
    except Exception as e:
        print(e)
        return HttpResponse(200)


# CampaignNotificationBackup
@require_POST
@csrf_exempt
def campaign_notification(request):

    new_sync = CampaignNotificationBackup.objects.create(req_body=f"{request.body}")

    return HttpResponse(200)


def pullData(request):
    try:
        allSub = UserSubscribtion.objects.all()
        allSubCount = allSub.count()
        print("allsub count", allSubCount)

        allActiveSubCount = allSub.filter(sub_active=True).count()
        print("allActiveSub count", allActiveSubCount)

        allRenewalSub = allSub.filter(renewal_sub=True, first_sub=False).count()
        print("all renewal sub", allRenewalSub)

    except Exception:
        pass

    return HttpResponse(200)


def generate_report(request):

    tasks.fetch_report.delay()
    tasks.subscribtion_source_report.delay()

    return HttpResponse(200)


def fetch_stats(request):
    today = datetime.now()
    the_day = request.GET.get("day", None)

    if the_day:
        date_format = "%Y-%m-%d %H:%M:%S"
        date_obj = datetime.strptime(f"{the_day} 00:00:00", date_format)
        day_1 = date_obj.replace(day=1)
        date_filter = Q(converted_at__date=date_obj.date())
        month_filter = Q(converted_at__date__range=(day_1.date(), date_obj.date()))
        backup_filter = Q(created_at__date=date_obj.date())
        remarketing_filter = Q(created_at__date__range=(day_1.date(), date_obj.date()))
        user_filter = Q(created_at__date=date_obj.date())
        datasync_filter = Q(created_at__date=date_obj.date())
    else:
        date_filter = Q(converted_at__month=today.month)
        month_filter = date_filter
        backup_filter = Q(created_at__month=today.month)
        remarketing_filter = backup_filter
        user_filter = backup_filter
        datasync_filter = Q(created_at__month=today.month)

    providers = [
        ("NETH", choices.CampaignProvider.NETH.value),
        ("MOBPLUS", choices.CampaignProvider.MOBPLUS.value),
        ("MOBIDEA", choices.CampaignProvider.MOBIDEA.value),
        ("ANGEL MEDIA", choices.CampaignProvider.ANGELMEDIA.value),
        ("KMMOBI", choices.CampaignProvider.KMMOBI.value),
        ("MOBIKOK", choices.CampaignProvider.MOBIKOK.value),
        ("SHINE", choices.CampaignProvider.SHINE.value),
        ("MOBIPIUM", choices.CampaignProvider.MOBIPIUM.value),
    ]

    campaign_counts_today = {}
    campaign_counts_month = {}

    for label, provider in providers:
        base_qs = CampaignTracker.objects.filter(provider=provider, converted=True)
        today_count = base_qs.filter(date_filter).count()
        month_count = base_qs.filter(month_filter).count()
        campaign_counts_today[label] = today_count
        campaign_counts_month[label] = month_count

    campaign_not = CampaignNotificationBackup.objects.filter(backup_filter).count()

    remarketing_today = CampaignDuplicate.objects.filter(
        backup_filter, remarketed=True
    ).count()
    remarketing_month = CampaignDuplicate.objects.filter(
        remarketing_filter, remarketed=True
    ).count()

    user_prof = UserProfile.objects.filter(user_filter).count()

    datasync_qs = DataSync.objects.filter(datasync_filter)
    subscriptions = datasync_qs.filter(type="SYNC_NOTIFICATION")
    renewals = datasync_qs.filter(type="RENEWAL_NOTIFICATION")
    unsubs = datasync_qs.filter(type="UNSUBSCRIPTION_NOTIFICATION")

    sub_revenue = subscriptions.aggregate(total=Sum("amount"))["total"] or 0
    renewals_revenue = renewals.aggregate(total=Sum("amount"))["total"] or 0
    total_revenue = sub_revenue + renewals_revenue

    # upstream
    upstream = subscriptions.filter(telco_ref__icontains="upstream_paid").distinct(
        "phone"
    )

    # Compose the final response
    data = {
        "New Users Aquisition": user_prof,
        "Web Traffic [Re-Marketing][Today]": remarketing_today,
        "Web Traffic [Re-Marketing][Month Count]": remarketing_month,
        "Upstream[Today]": upstream.count(),
        "campaign_notifications": campaign_not,
        "Revenue Data": {
            "New Subscribtion Count": subscriptions.count(),
            "New Subscribtion Revenue": sub_revenue,
            "Renewal Count": renewals.count(),
            "Renewal Revenue": renewals_revenue,
            "Unsubscription Count": unsubs.count(),
            "Total Revenue": total_revenue,
        },
    }

    for label in campaign_counts_today:
        data[f"WT [{label}][Today]"] = campaign_counts_today[label]
        data[f"WT [{label}][Month Count]"] = campaign_counts_month[label]

    return JsonResponse(data)


def get_cr_data(request):
    today = datetime.now()
    the_day = request.GET.get("day", None)
    if the_day:
        date_format = "%Y-%m-%d %H:%M:%S"
        date_obj = datetime.strptime(f"{the_day} 00:00:00", date_format).date()
    else:
        date_obj = today.date()

    partner = request.GET.get("partner")
    if not partner:
        return JsonResponse({"status": 400, "message": "Partner required"})

    tracks_qs = CampaignTracker.objects.filter(
        created_at__date=date_obj,
        provider=partner,
    )
    unique_tracks = tracks_qs.filter(occurence=0)
    converted = tracks_qs.filter(converted=True)

    traffic_hits = tracks_qs.count()
    unique_traffic = unique_tracks.count()
    converted_count = converted.count()

    print(
        f"traffic_hits:{traffic_hits}, unique_traffic:{unique_traffic}, converted_count:{converted_count}",
    )

    try:
        cr = (converted_count / traffic_hits) * 100
    except Exception:
        cr = 0

    data = {
        "Traffic Hit": traffic_hits,
        "Unique Traffic Hits": unique_traffic,
        "Converted": converted_count,
        "CR": cr,
    }
    return JsonResponse(data)


# @require_POST
# @csrf_exempt
# def data_sync_v2(request):
#     try:
#         print(f"Receiving datasync payload for: {request.body}")
#         the_data = json.loads(request.body)
#         datasync_task = tasks.process_datasync.delay(the_data)
#         if not datasync_task.id:
#             return JsonResponse({"status": 400, "error": "Unable to process request"})
#         result = AsyncResult(datasync_task.id, app=celery_app)
#         return JsonResponse({"status": 200, "message": "ok", "process_result":{
#             "task_id": datasync_task.id,
#             "task_status": result.status,
#             "result": result.result if result.ready() else None,
#         }})
#     except Exception as ex:
#         print(ex)
#         return JsonResponse({"status": 400, "error": "Unable to process request", "details": str(ex)})


@require_POST
@csrf_exempt
def data_sync_v2(request):
    try:
        tasks.share_datasync.delay(request.body.decode("utf-8"))
        WebhookBackup.objects.create(req_body=f"{request.body.decode('utf-8')}")
        print(f"Receiving datasync payload for: {request.body}")
        the_data = json.loads(request.body.decode("utf-8"))
        datasync_task = tasks.process_datasync(the_data)
        if datasync_task["status"] == "Failed":
            return JsonResponse(
                {
                    "status": 400,
                    "error": f"Unable to process request-{datasync_task["error"]}",
                },
                status=400,
            )
        return JsonResponse(
            {
                "status": 200,
                "message": "ok, [gamezhood] data sync processed successfully",
            }
        )
    except Exception as ex:
        print(ex)
        return JsonResponse(
            {"status": 400, "error": "Unable to process request", "details": str(ex)},
            status=400,
        )


def check_task_result(request):
    task_id = request.GET.get("task_id", None)
    if not task_id:
        return JsonResponse({"status": 400, "error": "task_id is required"})

    result = AsyncResult(task_id, app=celery_app)

    if result.ready():
        return JsonResponse(
            {"status": 200, "message": "Task completed", "result": result.result}
        )
    else:
        return JsonResponse(
            {
                "status": 202,
                "message": "Task is still processing",
                "task_status": result.status,
                "result": result.result if result.ready() else None,
            }
        )


def fetch_campaign_behaviour(request):

    start = request.GET.get("start", None)
    end = request.GET.get("end", None)

    if not start:
        return JsonResponse({"status": 400, "error": "start date is required"})
    if not end:
        return JsonResponse({"status": 400, "error": "end date is required"})

    if not datetime.strptime(start, "%Y-%m-%d"):
        return JsonResponse({"status": 400, "error": "invalid start date"})
    if not datetime.strptime(end, "%Y-%m-%d"):
        return JsonResponse({"status": 400, "error": "invalid end date"})

    tasks.campaign_behaviour.delay(start, end)

    return JsonResponse({"status": 200, "message": "Processing report!"})


def fetch_campaign_behaviour_daily(request):
    start = request.GET.get("start", None)
    end = request.GET.get("end", None)

    if not start:
        return JsonResponse({"status": 400, "error": "start date is required"})
    if not end:
        return JsonResponse({"status": 400, "error": "end date is required"})

    start_date = datetime.strptime(start, "%Y-%m-%d")
    end_date = datetime.strptime(end, "%Y-%m-%d")

    if (end_date - start_date).days > 30:
        return JsonResponse({"status": 400, "message": "Max date range is 30 days"})

    tasks.campaign_behaviour_daily_report.delay(start, end)

    return JsonResponse({"status": 200, "message": "Processing report!"})


def pull_3rd_party_acquisition_report(request):

    tasks.pull_3rd_party_acquisition_count.delay()

    return JsonResponse({"status": 200, "message": "Processing report!"})


def cleanup_campaign_tracker(request):

    month_num = request.GET.get("month", None)

    tasks.cleanup_camp_tracker.delay(month_num)

    return JsonResponse({"status": 200, "message": "Processing report!"})


def cleanup_data_sync(request):

    month_num = request.GET.get("month", None)

    tasks.cleanup_data_sync.delay(month_num)

    return JsonResponse({"status": 200, "message": "Processing report!"})


def export_all_msisdn_query(request):

    tasks.export_all_msisdns.delay()

    return JsonResponse({"status": 200, "message": "Processing report!"})


# def mobplus_campaign_url(request):
#     try:
#         partner = request.GET.get("partner", None)
#         click_id = request.GET.get("clickid", None)
#         telco = request.GET.get("telco", None)
#         pubid = request.GET.get("pubid", None)

#         unique_sub_ref = get_random_string(length=48)
#         msisdn = request.headers.get("Msisdn")
#         if not msisdn:
#             traffic_source = "OrganicSource"
#             redirect_url = f"http://mtn-nigeria-prod.mfilterit.org/sid/234102200008007?origin_banner=1&trxId={unique_sub_ref}&trfsrc={traffic_source}"
#             return HttpResponseRedirect(redirect_url)

#         if msisdn.startswith("0") and len(msisdn) == 11:
#             msisdn = msisdn.replace("0", "234", 1)

#         new_promo_hit = CampaignTracker.objects.filter(
#             click_id=click_id, provider=choices.CampaignProvider.MOBPLUS.value
#         ).last()
#         if not new_promo_hit:
#             new_promo_hit = CampaignTracker.objects.create(
#                 click_id=click_id,
#                 msisdn=msisdn,
#                 provider=choices.CampaignProvider.MOBPLUS.value,
#                 currency="USD",
#             )

#         if any([partner, telco, pubid]):
#             new_promo_hit.partner = partner or new_promo_hit.partner
#             new_promo_hit.telco = telco or new_promo_hit.telco
#             new_promo_hit.pubid = pubid or new_promo_hit.pubid
#             # new_promo_hit.save()


#         user_prof = UserProfile.objects.filter(phone=msisdn).first()
#         if user_prof:
#             # check if user has active subscribtion
#             now = timezone.now()
#             one_month_ago = now - relativedelta(hours=24)
#             # user deactivated active subscribtion
#             user_sub = UserSubscribtion.objects.filter(user=user_prof).first()
#             if user_sub.ends_date and user_sub.ends_date <= one_month_ago:
#                 tasks.handle_remarketing.apply_async(
#                 args=[msisdn, choices.CampaignProvider.MOBPLUS.value],
#                 countdown=120,
#                 )
#                 # redirect to secured D
#                 new_promo_hit.is_convertable = False
#                 ### redirect as organic source
#                 traffic_source = "OrganicSource"
#                 redirect_url = f"http://mtn-nigeria-prod.mfilterit.org/sid/234102200008007?origin_banner=1&trxId={unique_sub_ref}&trfsrc={traffic_source}"
#                 return HttpResponseRedirect(redirect_url)
#             else:
#                 return redirect("core:home")

#         new_promo_hit.save()
#         tasks.handle_occurence.delay(new_promo_hit.id)
#         traffic_source = "MobPlus"
#         redirect_url = f"http://mtn-nigeria-prod.mfilterit.org/sid/234102200008007?origin_banner=1&trxId={unique_sub_ref}&trfsrc={traffic_source}"
#         return HttpResponseRedirect(redirect_url)
#     except Exception as ex:
#         logger.error("exception occurred", exc_info=True)
#         return redirect("core:home")


def mobplus_campaign_url(request):
    try:
        partner = request.GET.get("partner", None)
        click_id = request.GET.get("clickid", None)
        telco = request.GET.get("telco", None)
        pubid = request.GET.get("pubid", None)

        unique_sub_ref = get_random_string(length=48)

        new_promo_hit = CampaignTracker.objects.filter(
            click_id=click_id, provider=choices.CampaignProvider.MOBPLUS.value
        ).last()
        if not new_promo_hit:
            new_promo_hit = CampaignTracker.objects.create(
                click_id=click_id,
                provider=choices.CampaignProvider.MOBPLUS.value,
                currency="USD",
            )

        if any([partner, telco, pubid]):
            new_promo_hit.partner = partner or new_promo_hit.partner
            new_promo_hit.telco = telco or new_promo_hit.telco
            new_promo_hit.pubid = pubid or new_promo_hit.pubid

        msisdn = request.headers.get("Msisdn")
        if msisdn:
            if msisdn.startswith("0") and len(msisdn) == 11:
                msisdn = msisdn.replace("0", "234", 1)

            new_promo_hit.msisdn = msisdn

        new_promo_hit.save()
        traffic_source = "MobPlus"
        redirect_url = f"http://mtn-nigeria-prod.mfilterit.org/sid/234102200008007?origin_banner=1&trxId={unique_sub_ref}&trfsrc={traffic_source}"
        return HttpResponseRedirect(redirect_url)
    except Exception:
        logger.error("exception occurred", exc_info=True)
        return redirect("content:home")


@require_GET
@csrf_exempt
def check_sub_status(request):
    data = dict(request.headers)

    json_resp = {}

    msisdn_data = data.get("Msisdn")
    if msisdn_data:
        msisdn = data["Msisdn"]
        if msisdn.startswith("0") and len(msisdn) == 11:
            msisdn = msisdn.replace("0", "234", 1)

        theUser, _ = UserProfile.objects.get_or_create(phone=msisdn)
        fetchSubscribtion = UserSubscribtion.objects.filter(user=theUser)
        if fetchSubscribtion.exists():
            theSub = fetchSubscribtion.first()
            if theSub.sub_active == True:
                json_resp.update(
                    {
                        "status": True,
                        "message": "Msisdn has active subscribtion",
                    }
                )
            else:
                json_resp.update(
                    {
                        "status": False,
                        "message": "No Active subscribtion",
                    }
                )
        else:
            json_resp.update(
                {
                    "status": False,
                    "message": "No Active subscribtion",
                }
            )
    else:
        json_resp.update(
            {
                "status": False,
                "message": "No Active subscribtion",
            }
        )

    return JsonResponse(
        data=json_resp,
    )


# def kmmobi_campaign_url(request):
#     try:
#         partner = request.GET.get("partner", None)
#         click_id = request.GET.get("clickid", None)
#         telco = request.GET.get("telco", None)
#         pubid = request.GET.get("pubid", None)

#         unique_sub_ref = get_random_string(length=48)
#         msisdn = request.headers.get("Msisdn")
#         if not msisdn:
#             traffic_source = "OrganicSource"
#             redirect_url = f"http://mtn-nigeria-prod.mfilterit.org/sid/234102200008007?origin_banner=1&trxId={unique_sub_ref}&trfsrc={traffic_source}"
#             return HttpResponseRedirect(redirect_url)

#         if msisdn.startswith("0") and len(msisdn) == 11:
#             msisdn = msisdn.replace("0", "234", 1)

#         new_promo_hit = CampaignTracker.objects.filter(
#             click_id=click_id, provider=choices.CampaignProvider.KMMOBI.value
#         ).last()
#         if not new_promo_hit:
#             new_promo_hit = CampaignTracker.objects.create(
#                 click_id=click_id,
#                 msisdn=msisdn,
#                 provider=choices.CampaignProvider.KMMOBI.value,
#                 currency="USD",
#             )

#         if any([partner, telco, pubid]):
#             new_promo_hit.partner = partner or new_promo_hit.partner
#             new_promo_hit.telco = telco or new_promo_hit.telco
#             new_promo_hit.pubid = pubid or new_promo_hit.pubid
#             # new_promo_hit.save()


#         user_prof = UserProfile.objects.filter(phone=msisdn).first()
#         if user_prof:
#             # check if user has active subscribtion
#             now = timezone.now()
#             one_month_ago = now - relativedelta(hours=24)
#             # user deactivated active subscribtion
#             user_sub = UserSubscribtion.objects.filter(user=user_prof).first()
#             if user_sub.ends_date and user_sub.ends_date <= one_month_ago:
#                 tasks.handle_remarketing.apply_async(
#                 args=[msisdn, choices.CampaignProvider.KMMOBI.value],
#                 countdown=120,
#                 )
#                 # redirect to secured D
#                 new_promo_hit.is_convertable = False
#                 ### redirect as organic source
#                 traffic_source = "OrganicSource"
#                 redirect_url = f"http://mtn-nigeria-prod.mfilterit.org/sid/234102200008007?origin_banner=1&trxId={unique_sub_ref}&trfsrc={traffic_source}"
#                 return HttpResponseRedirect(redirect_url)
#             else:
#                 return redirect("content:home")

#         new_promo_hit.save()
#         tasks.handle_occurence.delay(new_promo_hit.id)
#         traffic_source = "KM Mobi"
#         redirect_url = f"http://mtn-nigeria-prod.mfilterit.org/sid/234102200008007?origin_banner=1&trxId={unique_sub_ref}&trfsrc={traffic_source}"
#         return HttpResponseRedirect(redirect_url)
#     except Exception as ex:
#         logger.error("exception occurred", exc_info=True)
#         return redirect("content:home")


def kmmobi_campaign_url(request):
    return redirect("content:home")
    try:
        partner = request.GET.get("partner", None)
        click_id = request.GET.get("clickid", None)
        telco = request.GET.get("telco", None)
        pubid = request.GET.get("pubid", None)

        unique_sub_ref = get_random_string(length=48)

        new_promo_hit = CampaignTracker.objects.filter(
            click_id=click_id, provider=choices.CampaignProvider.KMMOBI.value
        ).last()
        if not new_promo_hit:
            new_promo_hit = CampaignTracker.objects.create(
                click_id=click_id,
                provider=choices.CampaignProvider.KMMOBI.value,
                currency="USD",
            )

        if any([partner, telco, pubid]):
            new_promo_hit.partner = partner or new_promo_hit.partner
            new_promo_hit.telco = telco or new_promo_hit.telco
            new_promo_hit.pubid = pubid or new_promo_hit.pubid

        msisdn = request.headers.get("Msisdn")
        if msisdn:
            if msisdn.startswith("0") and len(msisdn) == 11:
                msisdn = msisdn.replace("0", "234", 1)

            new_promo_hit.msisdn = msisdn

        new_promo_hit.save()
        traffic_source = "KM Mobi"
        redirect_url = f"http://mtn-nigeria-prod.mfilterit.org/sid/234102200008007?origin_banner=1&trxId={unique_sub_ref}&trfsrc={traffic_source}"
        return HttpResponseRedirect(redirect_url)
    except Exception:
        logger.error("exception occurred", exc_info=True)
        return redirect("content:home")


def mobikok_campaign_url(request):
    return redirect("content:home")
    try:
        partner = request.GET.get("partner", None)
        click_id = request.GET.get("clickid", None)
        telco = request.GET.get("telco", None)
        pubid = request.GET.get("pubid", None)

        unique_sub_ref = get_random_string(length=48)

        new_promo_hit = CampaignTracker.objects.filter(
            click_id=click_id, provider=choices.CampaignProvider.MOBIKOK.value
        ).last()
        if not new_promo_hit:
            new_promo_hit = CampaignTracker.objects.create(
                click_id=click_id,
                provider=choices.CampaignProvider.MOBIKOK.value,
                currency="USD",
            )

        if any([partner, telco, pubid]):
            new_promo_hit.partner = partner or new_promo_hit.partner
            new_promo_hit.telco = telco or new_promo_hit.telco
            new_promo_hit.pubid = pubid or new_promo_hit.pubid

        msisdn = request.headers.get("Msisdn")
        if msisdn:
            if msisdn.startswith("0") and len(msisdn) == 11:
                msisdn = msisdn.replace("0", "234", 1)

            new_promo_hit.msisdn = msisdn

        new_promo_hit.save()
        traffic_source = "Mobikok"
        redirect_url = f"http://mtn-nigeria-prod.mfilterit.org/sid/234102200008007?origin_banner=1&trxId={unique_sub_ref}&trfsrc={traffic_source}"
        return HttpResponseRedirect(redirect_url)
    except Exception:
        logger.error("exception occurred", exc_info=True)
        return redirect("content:home")


def angel_media_campaign_url(request):
    return redirect("content:home")
    try:
        partner = request.GET.get("partner", None)
        click_id = request.GET.get("clickid", None)
        telco = request.GET.get("telco", None)
        pubid = request.GET.get("pubid", None)

        unique_sub_ref = get_random_string(length=48)

        new_promo_hit = CampaignTracker.objects.filter(
            click_id=click_id, provider=choices.CampaignProvider.ANGELMEDIA.value
        ).last()
        if not new_promo_hit:
            new_promo_hit = CampaignTracker.objects.create(
                click_id=click_id,
                provider=choices.CampaignProvider.ANGELMEDIA.value,
                currency="USD",
            )

        if any([partner, telco, pubid]):
            new_promo_hit.partner = partner or new_promo_hit.partner
            new_promo_hit.telco = telco or new_promo_hit.telco
            new_promo_hit.pubid = pubid or new_promo_hit.pubid

        msisdn = request.headers.get("Msisdn")
        if msisdn:
            if msisdn.startswith("0") and len(msisdn) == 11:
                msisdn = msisdn.replace("0", "234", 1)

            new_promo_hit.msisdn = msisdn

        new_promo_hit.save()
        traffic_source = "Janx"
        redirect_url = f"http://mtn-nigeria-prod.mfilterit.org/sid/234102200008007?origin_banner=1&trxId={unique_sub_ref}&trfsrc={traffic_source}"
        return HttpResponseRedirect(redirect_url)
    except Exception:
        logger.error("exception occurred", exc_info=True)
        return redirect("content:home")


def neth_campaign_url(request):
    try:
        partner = request.GET.get("partner", None)
        click_id = request.GET.get("clickid", None)
        telco = request.GET.get("telco", None)
        pubid = request.GET.get("pubid", None)
        return redirect("content:home")

        unique_sub_ref = get_random_string(length=48)

        new_promo_hit = CampaignTracker.objects.filter(
            click_id=click_id, provider=choices.CampaignProvider.NETH.value
        ).last()
        if not new_promo_hit:
            new_promo_hit = CampaignTracker.objects.create(
                click_id=click_id,
                provider=choices.CampaignProvider.NETH.value,
                currency="USD",
            )

        if any([partner, telco, pubid]):
            new_promo_hit.partner = partner or new_promo_hit.partner
            new_promo_hit.telco = telco or new_promo_hit.telco
            new_promo_hit.pubid = pubid or new_promo_hit.pubid

        msisdn = request.headers.get("Msisdn")
        if msisdn:
            if msisdn.startswith("0") and len(msisdn) == 11:
                msisdn = msisdn.replace("0", "234", 1)

            new_promo_hit.msisdn = msisdn

        new_promo_hit.save()
        traffic_source = "Traffic Company"
        redirect_url = f"http://mtn-nigeria-prod.mfilterit.org/sid/234102200008007?origin_banner=1&trxId={unique_sub_ref}&trfsrc={traffic_source}"
        return HttpResponseRedirect(redirect_url)
    except Exception:
        logger.error("exception occurred", exc_info=True)
        return redirect("content:home")


def shine_campaign_url(request):
    return redirect("content:home")
    try:
        partner = request.GET.get("partner", None)
        click_id = request.GET.get("clickid", None)
        telco = request.GET.get("telco", None)
        pubid = request.GET.get("pubid", None)

        unique_sub_ref = get_random_string(length=48)

        new_promo_hit = CampaignTracker.objects.filter(
            click_id=click_id, provider=choices.CampaignProvider.SHINE.value
        ).last()
        if not new_promo_hit:
            new_promo_hit = CampaignTracker.objects.create(
                click_id=click_id,
                provider=choices.CampaignProvider.SHINE.value,
                currency="USD",
            )

        if any([partner, telco, pubid]):
            new_promo_hit.partner = partner or new_promo_hit.partner
            new_promo_hit.telco = telco or new_promo_hit.telco
            new_promo_hit.pubid = pubid or new_promo_hit.pubid

        msisdn = request.headers.get("Msisdn")
        if msisdn:
            if msisdn.startswith("0") and len(msisdn) == 11:
                msisdn = msisdn.replace("0", "234", 1)

            new_promo_hit.msisdn = msisdn

        new_promo_hit.save()
        traffic_source = "Shine Digital"
        redirect_url = f"http://mtn-nigeria-prod.mfilterit.org/sid/234102200008007?origin_banner=1&trxId={unique_sub_ref}&trfsrc={traffic_source}"
        return HttpResponseRedirect(redirect_url)
    except Exception:
        logger.error("exception occurred", exc_info=True)
        return redirect("content:home")


def mobipium_campaign_url(request):
    return redirect("content:home")
    try:
        partner = request.GET.get("partner", None)
        click_id = request.GET.get("clickid", None)
        telco = request.GET.get("telco", None)
        pubid = request.GET.get("pubid", None)

        unique_sub_ref = get_random_string(length=48)

        new_promo_hit = CampaignTracker.objects.filter(
            click_id=click_id, provider=choices.CampaignProvider.MOBIPIUM.value
        ).last()
        if not new_promo_hit:
            new_promo_hit = CampaignTracker.objects.create(
                click_id=click_id,
                provider=choices.CampaignProvider.MOBIPIUM.value,
                currency="USD",
            )

        if any([partner, telco, pubid]):
            new_promo_hit.partner = partner or new_promo_hit.partner
            new_promo_hit.telco = telco or new_promo_hit.telco
            new_promo_hit.pubid = pubid or new_promo_hit.pubid

        msisdn = request.headers.get("Msisdn")
        if msisdn:
            if msisdn.startswith("0") and len(msisdn) == 11:
                msisdn = msisdn.replace("0", "234", 1)

            new_promo_hit.msisdn = msisdn

        new_promo_hit.save()
        traffic_source = "Shine Digital"
        redirect_url = f"http://mtn-nigeria-prod.mfilterit.org/sid/234102200008007?origin_banner=1&trxId={unique_sub_ref}&trfsrc={traffic_source}"
        return HttpResponseRedirect(redirect_url)
    except Exception:
        logger.error("exception occurred", exc_info=True)
        return redirect("content:home")
