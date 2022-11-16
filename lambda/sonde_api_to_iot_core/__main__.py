from . import *
import json
import base64
import gzip
import uuid
body = [
    {
        "software_name": "radiosonde_auto_rx",
        "software_version": "1.5.9",
        "uploader_callsign": "DL1XH",
        "uploader_position": ["53.762","10.471",0],
        "uploader_antenna": "5/8 GP",
        "time_received": "2022-11-16T23:55:44.195615Z",
        "datetime": "2022-11-16T23:56:00.000000Z",
        "manufacturer": "Vaisala",
        "type": "potato",
        "serial": "T1240994",
        "subtype": "iMet-4",
        "frame": 5777,
        "lat": 54.6185,
        "lon": 11.23383,
        "alt": 23214.77006,
        "temp": -71.0,
        "humidity": 3.3,
        "pressure": 29.57,
        "vel_v": 3.53743,
        "vel_h": 43.32368,
        "heading": 105.07473,
        "sats": 10,
        "batt": 2.5,
        "frequency": 402.5,
        "burst_timer": 65535,
        "snr": 23.1,
        "tx_frequency": 402.5,
        "user-agent": "Amazon CloudFront",
        "position": "54.6185,11.23383",
        "upload_time_delta": -1.969,
        "uploader_alt": 45.0,
        "dev": True
    }
]

compressed = BytesIO()
with gzip.GzipFile(fileobj=compressed, mode='w') as f:
    f.write(json.dumps(body).encode('utf-8'))
compressed.seek(0)
bbody = base64.b64encode(compressed.read()).decode("utf-8")
payload = compressed.getvalue()
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
class fakeContext:
    def __init__(self):
        self.log_stream_name = str(uuid.uuid4())
print(lambda_handler(payload, fakeContext()))
