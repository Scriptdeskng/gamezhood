from django.db import models
from django.utils import timezone

import random, string

from django.db.models.signals import post_save
from django.conf import settings


from django.utils.translation import gettext_lazy as _

from . import choices


SUB_STATUS = (
    ("active", "Active"),
    ("inactive", "Inactive"),
    ("no_sub", "No Subscribtion"),
)


TEST_PHASE = (
    ("live_prod", "Live Prod"),
    ("phase_one", "Phase One"),
    ("phase_two", "Phase Two"),
    ("beta", "Beta"),
)


class WebhookBackup(models.Model):
    req_body = models.TextField(blank=True, null=True)
    telco = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.created_at}"


class UserProfile(models.Model):
    phone = models.CharField(
        max_length=40,
        null=True,
    )
    first_name = models.CharField(blank=True, null=True, max_length=200)
    last_name = models.CharField(blank=True, null=True, max_length=200)
    dob = models.DateField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=200, blank=True, null=True)
    state = models.CharField(max_length=200, blank=True, null=True)
    nationality = models.CharField(max_length=200, blank=True, null=True)
    test_phase = models.CharField(
        max_length=200, choices=TEST_PHASE, default="live_prod"
    )
    traffic_source = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        choices=choices.PROVIDER_CHOICES,
        verbose_name=_("traffic_source"),
    )
    sub_status = models.CharField(max_length=200, choices=SUB_STATUS, default="no_sub")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.phone}"


class UserSubscribtion(models.Model):
    user = models.ForeignKey("UserProfile", on_delete=models.CASCADE, null=True)
    sub_active = models.BooleanField(default=False)
    starts_date = models.DateTimeField(blank=True, null=True)
    ends_date = models.DateTimeField(blank=True, null=True)
    first_sub = models.BooleanField(default=False)
    renewal_sub = models.BooleanField(default=False)
    traffic_source = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        choices=choices.PROVIDER_CHOICES,
        verbose_name=_("traffic_source"),
    )
    auto_renewal = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user}"


class CampaignNotificationBackup(models.Model):
    req_body = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.created_at}"


class CampaignTracker(models.Model):
    msisdn = models.CharField(max_length=200, blank=True, null=True)
    partner = models.CharField(max_length=200, blank=True, null=True)
    click_id = models.CharField(max_length=200, blank=True, null=True)
    telco = models.CharField(max_length=200, blank=True, null=True)
    req_body = models.TextField(blank=True, null=True)
    # new mobplus integration
    provider = models.TextField(
        choices=choices.PROVIDER_CHOICES,
        default=choices.CampaignProvider.NETH.value,
        verbose_name=_("provider"),
    )
    pubid = models.CharField(max_length=200, blank=True, null=True)
    amt = models.CharField(max_length=200, blank=True, null=True)
    currency = models.CharField(max_length=200, blank=True, null=True)
    occurence = models.IntegerField(default=0)
    is_convertable = models.BooleanField(default=True)
    converted = models.BooleanField(default=False)
    converted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.click_id}"


class CampaignDuplicate(models.Model):
    msisdn = models.CharField(max_length=200, blank=True, null=True)
    provider = models.TextField(
        choices=choices.PROVIDER_CHOICES,
        blank=True,
        null=True,
        verbose_name=_("provider"),
    )
    occurence = models.IntegerField(default=1)
    remarketed = models.BooleanField(default=False)
    last_subscribtion = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)


class DataSync(models.Model):
    type = models.CharField(max_length=100, blank=True, null=True)
    telco = models.CharField(max_length=100, blank=True, null=True)
    product_id = models.CharField(max_length=100, blank=True, null=True)
    product_name = models.CharField(max_length=200, blank=True, null=True)
    product_not_type = models.CharField(max_length=100, blank=True, null=True)
    product_sub_type = models.CharField(max_length=100, blank=True, null=True)
    amount = models.IntegerField(default=0)
    channel = models.CharField(max_length=100, blank=True, null=True)
    auto_renewal = models.BooleanField(default=False)
    sub_date = models.DateTimeField(blank=True, null=True)
    sub_expiry = models.DateTimeField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    telco_ref = models.CharField(max_length=50, blank=True, null=True)
    webhook_backup = models.ForeignKey(
        WebhookBackup, on_delete=models.DO_NOTHING, blank=True, null=True
    )
    campaign_tracker = models.ForeignKey(
        CampaignTracker, on_delete=models.DO_NOTHING, blank=True, null=True
    )
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.type} - {self.phone}"


class VendorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    user_code = models.TextField(blank=True, null=True)
    first_name = models.TextField(blank=True, null=True)
    last_name = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.user.username

    @property
    def last_login(self, *args, **kwargs):
        the_last_login = self.user.last_login
        if the_last_login:
            user_last_login = the_last_login.strftime("%Y-%m-%d %H:%M")
            return user_last_login
        return None


def profile_receiver(sender, instance, created, *args, **kwargs):
    if created:
        profile = VendorProfile.objects.get_or_create(user=instance)

    profile, created = VendorProfile.objects.get_or_create(user=instance)
    if profile.user_code is None or profile.user_code == "":
        profile.user_code = str(
            "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        )
        profile.save()


post_save.connect(profile_receiver, sender=settings.AUTH_USER_MODEL)
