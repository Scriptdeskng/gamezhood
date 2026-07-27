##########

from ums.utils import resolve_msisdn_from_request


def fetch_msisdn(request):
    msisdn = resolve_msisdn_from_request(request)
    return {"msisdn": msisdn or "Anonymous User"}
