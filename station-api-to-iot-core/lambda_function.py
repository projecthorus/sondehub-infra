import json
import boto3
import zlib
import base64
import datetime
import functools
import uuid
import threading
from email.utils import parsedate
from botocore.awsrequest import AWSRequest
from botocore.endpoint import URLLib3Session
from botocore.auth import SigV4Auth
import boto3
import botocore.credentials

import os
from io import BytesIO
import gzip

from multiprocessing import Process
http_session = URLLib3Session()


def mirror(path,params):
    session = boto3.Session()
    headers = {"Host": "search-sondes-v2-hiwdpmnjbuckpbwfhhx65mweee.us-east-1.es.amazonaws.com", "Content-Type": "application/json", "Content-Encoding":"gzip"}
    request = AWSRequest(
        method="POST", url=f"https://search-sondes-v2-hiwdpmnjbuckpbwfhhx65mweee.us-east-1.es.amazonaws.com/{path}", data=params, headers=headers
    )
    SigV4Auth(boto3.Session().get_credentials(), "es", "us-east-1").add_auth(request)
    r = http_session.send(request.prepare())


HOST = os.getenv("ES")

def lambda_handler(event, context):
    if "isBase64Encoded" in event and event["isBase64Encoded"] == True:
        event["body"] = base64.b64decode(event["body"])
    if (
        "content-encoding" in event["headers"]
        and event["headers"]["content-encoding"] == "gzip"
    ):
        event["body"] = zlib.decompress(event["body"], 16 + zlib.MAX_WBITS)
    time_delta = None
    if "date" in event["headers"]:
        try:
            time_delta_header = event["headers"]["date"]
            time_delta = (
                datetime.datetime(*parsedate(time_delta_header)[:7])
                - datetime.datetime.utcfromtimestamp(event["requestContext"]["timeEpoch"]/1000)
            ).total_seconds()
        except:
            pass
    payload = json.loads(event["body"])
    print(payload)
    if "user-agent" in event["headers"]:
        event["time_server"] = datetime.datetime.now().isoformat()
        payload["user-agent"] = event["headers"]["user-agent"]
    if time_delta:
        payload["upload_time_delta"] = time_delta

    payload.pop("uploader_contact_email", None)

    # clean up None reports

    if "uploader_position" in payload and None in payload["uploader_position"]:
        payload.pop("uploader_position", None)
    
    if "uploader_position" in payload:
        (payload["uploader_alt"], payload["uploader_position_elk"]) = (
                payload["uploader_position"][2],
                f"{payload['uploader_position'][0]},{payload['uploader_position'][1]}",
            )
    index = datetime.datetime.utcnow().strftime("listeners-%Y-%m")
    payload["ts"] = datetime.datetime.utcnow().isoformat()

    es_request(json.dumps(payload),f"{index}/_doc","POST")

    return {"statusCode": 200, "body": "^v^ telm logged"}



def es_request(payload, path, method):
    # get aws creds
    session = boto3.Session()
    compressed = BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode='w') as f:
        f.write(payload.encode('utf-8'))
    payload = compressed.getvalue()
    headers = {"Host": HOST, "Content-Type": "application/json", "Content-Encoding":"gzip"}
    request = AWSRequest(
        method="POST", url=f"https://{HOST}/{path}", data=payload, headers=headers
    )
    SigV4Auth(boto3.Session().get_credentials(), "es", "us-east-1").add_auth(request)
    p = Process(target=mirror, args=(path,payload)).start()
    session = URLLib3Session()
    r = session.send(request.prepare())
    if r.status_code != 200 and r.status_code != 201:
        raise RuntimeError
    return json.loads(r.text)

if __name__ == "__main__":
    payload = {
        "version": "2.0",
        "routeKey": "PUT /sondes/telemetry",
        "rawPath": "/sondes/telemetry",
        "rawQueryString": "",
        "headers": {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate",
            "content-length": "2135",
            "content-type": "application/json",
            "host": "api.v2.sondehub.org",
            "user-agent": "autorx-1.4.1-beta4",
            "x-amzn-trace-id": "Root=1-6015f571-6aef2e73165042d53fcc317a",
            "x-forwarded-for": "103.107.130.22",
            "x-forwarded-port": "443",
            "x-forwarded-proto": "https",
            "date": "Sun, 31 Jan 2021 00:21:45 GMT",
        },
        "requestContext": {
            "accountId": "143841941773",
            "apiId": "r03szwwq41",
            "domainName": "api.v2.sondehub.org",
            "domainPrefix": "api",
            "http": {
                "method": "PUT",
                "path": "/sondes/telemetry",
                "protocol": "HTTP/1.1",
                "sourceIp": "103.107.130.22",
                "userAgent": "autorx-1.4.1-beta4",
            },
            "requestId": "Z_NJvh0RoAMEJaw=",
            "routeKey": "PUT /sondes/telemetry",
            "stage": "$default",
            "time": "31/Jan/2021:00:10:25 +0000",
            "timeEpoch": 1612051825409,
        },
        "body": """
        {
    "software_name": "radiosonde_auto_rx",
    "software_version": "1.5.5",
    "uploader_callsign": "mwheeler",
    "uploader_position": [
        -37.8136,
        144.9631,
        90
    ],
    "uploader_antenna": "mwheeler",
    "uploader_contact_email": "none@none.com",
    "mobile": false
}
        """,
        "isBase64Encoded": False,
    }
    print(lambda_handler(payload, {}))