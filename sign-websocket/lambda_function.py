import boto3
import time
import uuid
import urllib.parse
import hmac, datetime, hashlib
import os

#todo this will need an iam role that has iot connection privs

def aws_sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def aws_getSignatureKey(key, dateStamp, regionName, serviceName):
    kDate = aws_sign(("AWS4" + key).encode("utf-8"), dateStamp)
    kRegion = aws_sign(kDate, regionName)
    kService = aws_sign(kRegion, serviceName)
    kSigning = aws_sign(kService, "aws4_request")
    return kSigning


def aws_presign(
    access_key=None,
    secret_key=None,
    session_token=None,
    host=None,
    region=None,
    method=None,
    protocol=None,
    uri=None,
    service=None,
    expires=3600,
    payload_hash=None,
):
    # method=GET, protocol=wss, uri=/mqtt service=iotdevicegateway
    assert 604800 >= expires >= 1, "Invalid expire time 604800 >= %s >= 1" % expires

    # Date stuff, first is datetime, second is just date.
    t = datetime.datetime.utcnow()
    date_time = t.strftime("%Y%m%dT%H%M%SZ")
    date = t.strftime("%Y%m%d")
    # Signing algorithm used
    algorithm = "AWS4-HMAC-SHA256"

    # Scope of credentials, date + region (eu-west-1) + service (iot gateway hostname) + signature version
    credential_scope = date + "/" + region + "/" + service + "/" + "aws4_request"
    # Start building the query-string
    canonical_querystring = "X-Amz-Algorithm=" + algorithm
    canonical_querystring += "&X-Amz-Credential=" + urllib.parse.quote_plus(
        access_key + "/" + credential_scope
    )
    canonical_querystring += "&X-Amz-Date=" + date_time
    canonical_querystring += "&X-Amz-Expires=" + str(expires)
    canonical_querystring += "&X-Amz-SignedHeaders=host"

    if payload_hash is None:
        if service == "iotdevicegateway":
            payload_hash = hashlib.sha256(b"").hexdigest()
        else:
            payload_hash = "UNSIGNED-PAYLOAD"

    canonical_headers = "host:" + host + "\n"
    canonical_request = (
        method
        + "\n"
        + uri
        + "\n"
        + canonical_querystring
        + "\n"
        + canonical_headers
        + "\nhost\n"
        + payload_hash
    )

    string_to_sign = (
        algorithm
        + "\n"
        + date_time
        + "\n"
        + credential_scope
        + "\n"
        + hashlib.sha256(canonical_request.encode()).hexdigest()
    )
    signing_key = aws_getSignatureKey(secret_key, date, region, service)
    signature = hmac.new(
        signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    canonical_querystring += "&X-Amz-Signature=" + signature
    if session_token:
        canonical_querystring += "&X-Amz-Security-Token=" + urllib.parse.quote(
            session_token
        )

    return protocol + "://" + host + uri + "?" + canonical_querystring


def lambda_handler(event, context):
    #get aws creds
    session = boto3.Session()
    credentials = session.get_credentials()
    current_credentials = credentials.get_frozen_credentials()

    url = aws_presign(
        access_key=current_credentials.access_key,
        secret_key=current_credentials.secret_key,
        session_token=current_credentials.token,
        method="GET",
        protocol="wss",
        uri="/mqtt",
        service="iotdevicegateway",
        host=os.getenv("IOT_ENDPOINT"),
        region=session.region_name,
    )
    return {"statusCode": 200, "body": url}

if __name__ == "__main__":
    print(lambda_handler({}, {}))