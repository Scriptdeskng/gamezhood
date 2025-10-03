from django.urls import path
from .views import *


app_name = "users"

urlpatterns = [
    path("awaiting_response/", awaiting_response, name="awaiting_response"),
    path("onboarding/", onboarding, name="onboarding"),
    path("subscribe/", subscribe, name="subscribe"),
    path("cancelSubscribtion/", cancelSubscribtion, name="cancelSubscribtion"),
    path("inactive_account/", inactive_account, name="inactive_account"),
    path("data-sync/", data_sync_v2, name="data_sync_v2"),
    path("data_sync_endpoint/", data_sync, name="data_sync_endpoint"),
    path("campaign_notification/", campaign_notification, name="campaign_notification"),
    path("pullData/", pullData, name="pullData"),
    path("generate_report/", generate_report, name="generate-report"),
    path("fetch_stats/", fetch_stats, name="fetch_stats"),
    ##
    path("campaign-stats/", fetch_campaign_behaviour, name="fetch_campaign_behaviour"),
    path(
        "campaign-stats-daily/",
        fetch_campaign_behaviour_daily,
        name="fetch_campaign_behaviour_daily",
    ),
    path(
        "pull_3rd_party_acquisition_report/",
        pull_3rd_party_acquisition_report,
        name="pull_3rd_party_acquisition_report",
    ),
    path(
        "cleanup_campaign_tracker/",
        cleanup_campaign_tracker,
        name="cleanup_campaign_tracker",
    ),
    path("cleanup_data_sync/", cleanup_data_sync, name="cleanup_data_sync"),
    path("export_all_msisdn_query/", export_all_msisdn_query, name="export_all_msisdn_query"),

    #web promos 
    path("campaign/mobplus/", mobplus_campaign_url, name="campaign-mobplus"),
    path("campaign/kmmobi/", kmmobi_campaign_url, name="campaign-kmmobi"),
    path("campaign/mobikok/", mobikok_campaign_url, name="campaign-mobikok"),
    path("campaign/angel-media/", angel_media_campaign_url, name="campaign-angel-media"),
    path("campaign/tc/", neth_campaign_url, name="campaign-neth"),
    path("campaign/shine/", shine_campaign_url, name="campaign-shine"),
    path("campaign/mobipium/", mobipium_campaign_url, name="campaign-mobipium"),

    path(
        "get_cr_data/",
        get_cr_data,
        name="get_cr_data",
    ),

    path("check_sub_status/", check_sub_status, name="check_sub_status"),
    path("check_task_result/", check_task_result, name="check_task_result"),
]
