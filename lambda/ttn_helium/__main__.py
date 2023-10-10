from . import *
import json
import base64
import gzip
import uuid
from io import BytesIO

import sys

filename = "./helium/test_data.json"

_f = open(filename, 'r')
_json = json.loads(_f.read())

body = _json

compressed = BytesIO()
with gzip.GzipFile(fileobj=compressed, mode='w') as f:
    f.write(json.dumps(body).encode('utf-8'))
compressed.seek(0)
bbody = base64.b64encode(compressed.read()).decode("utf-8")



payload = {
    "version": "2.0",
    "routeKey": "POST /helium",
    "rawPath": "/helium",
    "rawQueryString": "",
    "headers": {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate",
        "content-encoding": "gzip",
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
            "method": "POST",
            "path": "/helium",
            "protocol": "HTTP/1.1",
            "sourceIp": "103.107.130.22",
            "userAgent": "everybody-needs-to-get-a-blimp",
        },
        "requestId": "Z_NJvh0RoAMEJaw=",
        "routeKey": "PUT /sondes/telemetry",
        "stage": "$default",
        "time": "31/Jan/2021:00:10:25 +0000",
        "timeEpoch": 1612051825409,
    },
    "body": bbody,
    "isBase64Encoded": True,
}
print(lambda_handler_helium(payload, {}))
