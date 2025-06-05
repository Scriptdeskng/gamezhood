from django.contrib import admin

from .models import *

# Register your models here.


admin.site.register(WebhookBackup)


# admin.site.register(UserProfile)
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        "phone",
        "sub_status",
        "traffic_source",
        "created_at",
    ]



admin.site.register(CampaignNotificationBackup)


@admin.register(UserSubscribtion)
class UserSubscribtionAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "sub_active",
        "starts_date",
        "traffic_source",
        "ends_date",
    ]
    search_fields = ["user__phone"]


@admin.register(CampaignTracker)
class CampaignTrackerAdmin(admin.ModelAdmin):
    list_display = [
        "msisdn",
        "partner",
        "amt",
        "click_id",
        "telco",
        "converted",
        "is_convertable",
        "occurence",
        "provider",
        "created_at",
        "converted_at",
    ]
    search_fields = ["msisdn", "click_id", "provider"]


@admin.register(CampaignDuplicate)
class CampaignDuplicateAdmin(admin.ModelAdmin):
    list_display = [
        "msisdn",
        "provider",
        "occurence",
        "remarketed",
        "last_subscribtion",
        "created_at",
    ]
    search_fields = ["msisdn"]


@admin.register(DataSync)
class DataSyncAdmin(admin.ModelAdmin):
    list_display = [
        "type",
        "telco",
        "product_id",
        "product_name",
        "product_not_type",
        "product_sub_type",
        "amount",
        "channel",
        "auto_renewal",
        "sub_date",
        "sub_expiry",
        "phone",
        "telco_ref",
        "webhook_backup",
        "campaign_tracker",
        "created_at",
    ]

    search_fields = ["phone", "type"]


@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "user_code",
        "first_name",
        "last_name",
    ]
