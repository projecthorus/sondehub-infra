from . import *
import json
import base64
import gzip
import uuid
body = [{
    "dev":True,
    "software_name": "SondeHubUploader", 
    "software_version": "1.0.0", 
    "uploader_callsign": "a", 
    "uploader_position": [53.23764, 7.74426, 7.0], 
    "uploader_antenna": "5/8-Wave-J-Pole",
    "time_received": "2023-01-22T22:48:43.208780Z",
    "datetime": "2023-01-22T22:48:41.000000Z",
    "manufacturer": "Vaisala", 
    "type": "RS41", 
    "serial": "U1440085",
    "frame": 1759, 
    "lat": 53.706667, 
    "lon": 7.146944, 
    "alt": 1295.7,
    "vel_v": 5.5, 
    "vel_h": 6.2,
    "heading": 222.0,
    "sats": 10, 
    "batt": 2.9, 
    "frequency": 404.1, 
    "rssi": 70.9
}]

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
