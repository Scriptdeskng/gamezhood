##########


def fetch_msisdn(request):
    if "Msisdn" in request.headers:
        msisdn = request.headers["Msisdn"]
        return {"msisdn": msisdn}
    else:
        return {"msisdn": "Anonymous User"}
