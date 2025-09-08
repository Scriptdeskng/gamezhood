from enum import unique

from content.enum import DocEnum
from django.utils.translation import gettext_lazy as _


@unique
class Roles(DocEnum):
    """
    User Roles
    """

    SuperAdmin = "Admin", "Super Admin user"
    Vendor = "Vendor", "Vendor Administrator User"
    SystemAdmin = "SystemAdmin", "System Administrator"


_readable_roles = {
    Roles.SuperAdmin.value: _("SuperAdmin"),
    Roles.Vendor.value: _("Vendor"),
    Roles.SystemAdmin.value: _("SystemAdmin"),
}


ROLE_CHOICES = [(d.value, _readable_roles[d.value]) for d in Roles]


@unique
class Telco(DocEnum):
    """
    Telco Choices
    """

    MTN = "MTN", "MTN"
    AIRTEL = "AIRTEL", "AIRTEL"


_readable_telcos = {
    Telco.MTN.value: _("MTN"),
    Telco.AIRTEL.value: _("AIRTEL"),
}


TELCO_CHOICES = [(d.value, _readable_telcos[d.value]) for d in Telco]


@unique
class CampaignProvider(DocEnum):
    """
    Campaign Provider Choices
    """

    NETH = "NETH", "NETH"
    MOBPLUS = "MOBPLUS", "MOBPLUS"
    MOBIDEA = "MOBIDEA", "MOBIDEA"
    ANGELMEDIA = "ANGELMEDIA", "ANGELMEDIA"
    KMMOBI = "KMMOBI", "KMMOBI"
    MOBIKOK = "MOBIKOK", "MOBIKOK"
    SHINE = "SHINE", "SHINE"


_readable_provider = {
    CampaignProvider.NETH.value: _("NETH"),
    CampaignProvider.MOBPLUS.value: _("MOBPLUS"),
    CampaignProvider.MOBIDEA.value: _("MOBIDEA"),
    CampaignProvider.ANGELMEDIA.value: _("ANGELMEDIA"),
    CampaignProvider.KMMOBI.value: _("KMMOBI"),
    CampaignProvider.MOBIKOK.value: _("MOBIKOK"),
    CampaignProvider.SHINE.value: _("SHINE"),
}


PROVIDER_CHOICES = [(d.value, _readable_provider[d.value]) for d in CampaignProvider]
