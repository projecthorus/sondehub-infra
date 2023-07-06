from . import *
import json
import base64
import gzip
import uuid
from io import BytesIO
body = [
    {
    "software_name": "radiosonde_auto_rx",
    "software_version": "1.5.5",
    "uploader_callsign": "sdf",
    "payload_callsign": "4FSKTEST",
    "uploader_antenna": "1/4 wave monopole",
    "time_received": "2021-12-30T03:55:05.510688Z",
    "datetime": "2021-12-30T03:55:05.510688Z",
    "manufacturer": "Graw",
    "type": "DFM",
    "subtype": "DFM09",
    "serial": "00000000",
    "frame": 1313391064,
    "lat": 47.8319,
    "lon": 10.89474,
    "alt": 1717.93,
    "temp": 7.4,
    "vel_v": 2.51,
    "vel_h": 8.18,
    "heading": 81.51,
    "sats": 9,
    "batt": 5.32,
    "frequency": 402.509,
    "snr": 13.3,
    "position": "47.8319,10.89474",
    "uploader_alt": 545,
    "uploader_position": [None,None,None],
  }]

compressed = BytesIO()
with gzip.GzipFile(fileobj=compressed, mode='w') as f:
    f.write(json.dumps(body).encode('utf-8'))
compressed.seek(0)
bbody = base64.b64encode(compressed.read()).decode("utf-8")



payload = {
    "version": "2.0",
    "routeKey": "PUT /sondes/telemetry",
    "rawPath": "/sondes/telemetry",
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
    "body": bbody,
    "isBase64Encoded": True,
}
print(lambda_handler(payload, {}))
