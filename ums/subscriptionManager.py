import requests
from datetime import datetime
from . import choices


telcoPrefixList = [
    # MTN
    {"prefix": "0803", "telco": "MTN"},
    {"prefix": "0806", "telco": "MTN"},
    {"prefix": "0814", "telco": "MTN"},
    {"prefix": "0810", "telco": "MTN"},
    {"prefix": "0813", "telco": "MTN"},
    {"prefix": "0814", "telco": "MTN"},
    {"prefix": "0816", "telco": "MTN"},
    {"prefix": "0703", "telco": "MTN"},
    {"prefix": "0704", "telco": "MTN"},
    {"prefix": "0706", "telco": "MTN"},
    {"prefix": "0903", "telco": "MTN"},
    {"prefix": "0906", "telco": "MTN"},
    # AIRTEL
    {"prefix": "0802", "telco": "AIRTEL"},
    {"prefix": "0808", "telco": "AIRTEL"},
    {"prefix": "0812", "telco": "AIRTEL"},
    {"prefix": "0708", "telco": "AIRTEL"},
    {"prefix": "0701", "telco": "AIRTEL"},
    {"prefix": "0902", "telco": "AIRTEL"},
    {"prefix": "0901", "telco": "AIRTEL"},
    {"prefix": "0904", "telco": "AIRTEL"},
    {"prefix": "0907", "telco": "AIRTEL"},
    {"prefix": "0911", "telco": "AIRTEL"},
    {"prefix": "0912", "telco": "AIRTEL"},
]


class HML:
    def __init__(self):
        self.mtn_base_url = "http://91.109.117.92:8001/api/v1/"
        self.airtel_base_url = "http://78.110.161.243:8001/api/v1/"
        # MTN
        self.mtnDailyProductID = "70"
        self.mtnWeeklyProductID = "71"
        self.mtnMonthlyProductID = "72"
        # Airtel
        self.airtelDailyProductID = "70"
        self.airtelWeeklyProductID = "71"
        self.airtelMonthlyProductID = "72"
        self.sms_channel = "SMS"
        self.telcoPrefix = telcoPrefixList

    def fetch_header(self):
        header = {"Authorization": "Bearer ClbUlFaBwT14g2xi2URb"}
        return header

    def format_msisdn(self, msisdn):
        if msisdn.startswith("234"):
            msisdn = msisdn.replace("234", "0", 1)
        return msisdn

    def format_234(self, msisdn):
        if msisdn.startswith("0") and len(msisdn) == 11:
            msisdn = msisdn.replace("0", "234", 1)
        return msisdn

    def checkNetwork(self, raw_msisdn):
        # change country code
        msisdn = self.format_msisdn(raw_msisdn)

        msisdn_prefix = msisdn[:4]

        found_prefix = next(
            (x for x in self.telcoPrefix if x["prefix"] == msisdn_prefix), False
        )
        if found_prefix:
            return found_prefix["telco"]

        return False

    def subscribe(self, msisdn, telco):
        try:
            base_url = (
                self.mtn_base_url
                if telco == choices.Telco.MTN.value
                else self.airtel_base_url
            )
            product_id = (
                self.mtnDailyProductID
                if telco == choices.Telco.MTN.value
                else self.airtelDailyProductID
            )
            data = {
                "product_id": product_id,
                "phone": self.format_msisdn(msisdn),
                "telco": telco,
                "channel": self.sms_channel,
            }

            response = requests.post(
                f"{base_url}product/subscription/initiate",
                json=data,
                headers=self.fetch_header(),
            )

            return response.json()
        except Exception as ex:
            print(ex)
            return False

    def unSubscribe(self, msisdn, telco):
        try:
            base_url = (
                self.mtn_base_url
                if telco == choices.Telco.MTN.value
                else self.airtel_base_url
            )
            product_id = (
                self.mtnDailyProductID
                if telco == choices.Telco.MTN.value
                else self.airtelDailyProductID
            )
            data = {
                "product_id": product_id,
                "phone": self.format_msisdn(msisdn),
                "telco": telco,
            }

            response = requests.post(
                f"{base_url}product/subscription/unsubscribe",
                json=data,
                headers=self.fetch_header(),
            )

            return response.json()
        except Exception as ex:
            print(ex)
            return False

    def checkPhoneStatus(self, msisdn, telco):
        try:
            base_url = (
                self.mtn_base_url
                if telco == choices.Telco.MTN.value
                else self.airtel_base_url
            )
            msisdn = self.format_234(msisdn)
            response = requests.post(
                f"{base_url}partner/report/subscribers/subscriber-status?phone={msisdn}",
                headers=self.fetch_header(),
            )

            return response.json()

        except Exception as ex:
            print(ex)
            return False
