from . import *

payload = {
    "version": "2.0",
    "routeKey": "PUT /recovered",
    "rawPath": "/recovered",
    "rawQueryString": "",
    "queryStringParameters": {
        #  "datetime": "2021-12-20T00:00",
        #   "duration": 1000000
        # "lat": "-32.7933",
        # "lon": "151.835",
        # "distance": "30000000"
        "serial": "S5031499"
    },
    "headers": {
        "accept": "*/*",
        "accept-encoding": "deflate",
        "content-encoding": "",
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
    "body": json.dumps({
        "datetime": "2021-06-06T01:10:07.629Z",
        "serial": "S4631407",
        "lat": 0,
        "lon": 0,
        "alt": 0,
        "recovered": True,
        "recovered_by": "string",
        "description": "string"
    }),
    "isBase64Encoded": False,
}
# print(put(payload, {}))
print(get(payload, {}))