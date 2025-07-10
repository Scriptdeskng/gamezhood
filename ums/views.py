from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.shortcuts import render, HttpResponse, redirect, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from content.mail import send_email

from dateutil.relativedelta import relativedelta

from django.db.models import Sum
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
        redirect_url = f"http://ng-app.com/AVANZAR/gamezhood-landing-en-doi-web?origin_banner=1&trxId={res}&trfsrc={traffic_source}"
        return redirect(redirect_url)
    except Exception as ex:
        print(ex)
        return redirect("content:home")

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
            return redirect("content:home")
        else:
            print("Subscribtion UnSuccessfull")
            return redirect("content:home")
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
            try:
                new_sync.telco = "AIRTEL"
                new_sync.save()
            except:
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
    
    new_sync = CampaignNotificationBackup.objects.create(
        req_body=f"{request.body}"
    )
      

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

    except Exception as e:
        pass

    return HttpResponse(200)


def generate_report(request):
   

    tasks.fetch_report.delay()
    tasks.subscribtion_source_report.delay()

    return HttpResponse(200)


#### Vendor Onboarding
def fetch_stats(request):
    today = datetime.now()

    # start_date_str = "2024-06-24 00:00:01"
    the_day = request.GET.get("day", None)
    if the_day:
        date_format = "%Y-%m-%d %H:%M:%S"
        date_obj = datetime.strptime(f"{the_day} 00:00:00", date_format)

        campaing_tracker_neth = CampaignTracker.objects.filter(
            created_at__date=date_obj.date(),
            provider=choices.CampaignProvider.NETH.value,
            converted=True,
        ).count()

        campaing_tracker_neth_month = CampaignTracker.objects.filter(
            created_at__month=date_obj.month,
            provider=choices.CampaignProvider.NETH.value,
            converted=True,
        ).count()

        campaing_tracker_mobedia = CampaignTracker.objects.filter(
            created_at__date=date_obj.date(),
            provider=choices.CampaignProvider.MOBIDEA.value,
            converted=True,
        ).count()

        campaing_tracker_mobedia_month = CampaignTracker.objects.filter(
            created_at__month=date_obj.month,
            provider=choices.CampaignProvider.MOBIDEA.value,
            converted=True,
        ).count()

        campaing_tracker_angel = CampaignTracker.objects.filter(
            created_at__date=date_obj.date(),
            provider=choices.CampaignProvider.ANGELMEDIA.value,
            converted=True,
        ).count()

        campaing_tracker_angel_month = CampaignTracker.objects.filter(
            created_at__month=date_obj.month,
            provider=choices.CampaignProvider.ANGELMEDIA.value,
            converted=True,
        ).count()

        campaing_tracker_mob = CampaignTracker.objects.filter(
            created_at__date=date_obj.date(),
            provider=choices.CampaignProvider.MOBPLUS.value,
            converted=True,
        ).count()

        campaing_tracker_mob_month = CampaignTracker.objects.filter(
            created_at__month=date_obj.month,
            provider=choices.CampaignProvider.MOBPLUS.value,
            converted=True,
        ).count()

        campaign_not = CampaignNotificationBackup.objects.filter(
            created_at__date=date_obj.date()
        ).count()

        user_prof = UserProfile.objects.filter(created_at__date=date_obj.date()).count()

        ## revenues
        datasync_qs = DataSync.objects.filter(created_at__date=date_obj.date())

        subscriptions = datasync_qs.filter(type="SYNC_NOTIFICATION")
        sub_revenue = (
            subscriptions.aggregate(total=Sum("amount"))["total"]
            if subscriptions.exists()
            else 0
        )

        unsubs = datasync_qs.filter(type="UNSUBSCRIPTION_NOTIFICATION")

        renewals = datasync_qs.filter(type="RENEWAL_NOTIFICATION")
        renewals_revenue = (
            renewals.aggregate(total=Sum("amount"))["total"] if renewals.exists() else 0
        )

        total_revenue = sub_revenue + renewals_revenue

    else:
        campaing_tracker_neth = CampaignTracker.objects.filter(
            created_at__month=today.month,
            converted=True,
            provider=choices.CampaignProvider.NETH.value,
        ).count()

        campaing_tracker_neth_month = campaing_tracker_neth

        campaing_tracker_mobedia = CampaignTracker.objects.filter(
            created_at__month=today.month,
            converted=True,
            provider=choices.CampaignProvider.MOBIDEA.value,
        ).count()

        campaing_tracker_mobedia_month = campaing_tracker_mobedia

        campaing_tracker_angel = CampaignTracker.objects.filter(
            created_at__month=today.month,
            provider=choices.CampaignProvider.ANGELMEDIA.value,
            converted=True,
        ).count()

        campaing_tracker_angel_month = campaing_tracker_angel

        campaing_tracker_mob = CampaignTracker.objects.filter(
            created_at__month=today.month,
            converted=True,
            provider=choices.CampaignProvider.MOBPLUS.value,
        ).count()

        campaing_tracker_mob_month = campaing_tracker_mob

        campaign_not = CampaignNotificationBackup.objects.filter(
            created_at__month=today.month
        ).count()

        user_prof = UserProfile.objects.filter(created_at__month=today.month).count()
        # revenue

        datasync_qs = DataSync.objects.filter(created_at__month=today.month)

        subscriptions = datasync_qs.filter(type="SYNC_NOTIFICATION")
        sub_revenue = (
            subscriptions.aggregate(total=Sum("amount"))["total"]
            if subscriptions.exists()
            else 0
        )

        unsubs = datasync_qs.filter(type="UNSUBSCRIPTION_NOTIFICATION")

        renewals = datasync_qs.filter(type="RENEWAL_NOTIFICATION")
        renewals_revenue = (
            renewals.aggregate(total=Sum("amount"))["total"] if renewals.exists() else 0
        )

        total_revenue = sub_revenue + renewals_revenue

    data = {
        "New Users Aquisition": user_prof,
        "Web Traffic Conversions[Daan]": campaing_tracker_neth,
        "Web Traffic Conversions[Daan][Month Count]": campaing_tracker_neth_month,
        "Web Traffic Conversions[MobPlus]": campaing_tracker_mob,
        "Web Traffic Conversions[MobPlus][Month Count]": campaing_tracker_mob_month,
        "Web Traffic [MOBEDIA][Today]": campaing_tracker_mobedia,
        "Web Traffic [MOBEDIA][Month Count]": campaing_tracker_mobedia_month,
        "Web Traffic [ANGEL MEDIA][Today]": campaing_tracker_angel,
        "Web Traffic [ANGEL MEDIA][Month Count]": campaing_tracker_angel_month,
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
    print(f"data is {data}")
    try:
        EMAIL_SUBJECT = f"GameSplash Fetch stats Report for {the_day}"
        REPORTING_MSG = f"""
            Hello Admin,
            Please find the report for {the_day}.
            {data}
            Regards.
            """.format()
        send_email(
            recipients=[
                "olushola@scriptdeskng.com",
                "adeola.olalekan@cloudintegratedinc.com",
            ],
            subject=EMAIL_SUBJECT,
            body_text=REPORTING_MSG,
            quiet=False,
        )
    except Exception as ex:
        print(ex)
        pass
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
        print(f"Receiving datasync payload for: {request.body}")
        the_data = json.loads(request.body)
        tasks.process_datasync(the_data)
        return JsonResponse({"status": 200, "message": "ok"})
    except Exception as ex:
        print(ex)
        return JsonResponse({"status": 400, "error": "Unable to process request", "details": str(ex)})


def check_task_result(request):
    task_id = request.GET.get("task_id", None)
    if not task_id:
        return JsonResponse({"status": 400, "error": "task_id is required"})

    result = AsyncResult(task_id, app=celery_app)

    if result.ready():
        return JsonResponse({
            "status": 200,
            "message": "Task completed",
            "result": result.result
        })
    else:
        return JsonResponse({
            "status": 202,
            "message": "Task is still processing",
            "task_status": result.status,
            "result": result.result if result.ready() else None,
        })
    

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




def mobplus_campaign_url(request):
    try:
        partner = request.GET.get("partner", None)
        click_id = request.GET.get("clickid", None)
        telco = request.GET.get("telco", None)
        pubid = request.GET.get("pubid", None)

        unique_sub_ref = get_random_string(length=48)
        msisdn = request.headers.get("Msisdn")
        if not msisdn:
            traffic_source = "OrganicSource"
            redirect_url = f"http://ng-app.com/AVANZAR/gamezhood-landing-en-doi-web?origin_banner=1&trxId={unique_sub_ref}&trfsrc={traffic_source}"
            return HttpResponseRedirect(redirect_url)

        if msisdn.startswith("0") and len(msisdn) == 11:
            msisdn = msisdn.replace("0", "234", 1)

        new_promo_hit = CampaignTracker.objects.filter(
            click_id=click_id, provider=choices.CampaignProvider.MOBPLUS.value
        ).last()
        if not new_promo_hit:
            new_promo_hit = CampaignTracker.objects.create(
                click_id=click_id,
                msisdn=msisdn,
                provider=choices.CampaignProvider.MOBPLUS.value,
                currency="USD",
            )

        if any([partner, telco, pubid]):
            new_promo_hit.partner = partner or new_promo_hit.partner
            new_promo_hit.telco = telco or new_promo_hit.telco
            new_promo_hit.pubid = pubid or new_promo_hit.pubid
            # new_promo_hit.save() 
        

        user_prof = UserProfile.objects.filter(phone=msisdn).first()
        if user_prof:
            # check if user has active subscribtion
            now = timezone.now()
            one_month_ago = now - relativedelta(hours=24)
            # user deactivated active subscribtion
            user_sub = UserSubscribtion.objects.filter(user=user_prof).first()
            if user_sub.ends_date and user_sub.ends_date <= one_month_ago:
                tasks.handle_remarketing.apply_async(
                args=[msisdn, choices.CampaignProvider.MOBPLUS.value],
                countdown=120,
                )
                # redirect to secured D
                new_promo_hit.is_convertable = False
                ### redirect as organic source
                traffic_source = "OrganicSource"
                redirect_url = f"http://ng-app.com/AVANZAR/gamezhood-landing-en-doi-web?origin_banner=1&trxId={unique_sub_ref}&trfsrc={traffic_source}"
                return HttpResponseRedirect(redirect_url)
            else:
                return redirect("content:home")

        new_promo_hit.save()
        tasks.handle_occurence.delay(new_promo_hit.id)
        traffic_source = "MobPlus"
        redirect_url = f"http://ng-app.com/AVANZAR/gamezhood-landing-en-doi-web?origin_banner=1&trxId={unique_sub_ref}&trfsrc={traffic_source}"
        return HttpResponseRedirect(redirect_url)
    except Exception as ex:
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
