from . import *
payload = {
    "version": "2.0",
    "routeKey": "PUT /tiles/count",
    "rawPath": "/tiles/count",
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
            "path": "/tiles/count",
            "protocol": "HTTP/1.1",
            "sourceIp": "103.107.130.22",
            "userAgent": "autorx-1.4.1-beta4",
        },
        "requestId": "Z_NJvh0RoAMEJaw=",
        "routeKey": "PUT /tiles/count",
        "stage": "$default",
        "time": "31/Jan/2021:00:10:25 +0000",
        "timeEpoch": 1612051825409,
    },
    "body": """
{
    "client": "SondeHub-Tracker-1581027979",
    "tile_loads": {
        "Mapnik": 82,
        "DarkMatter": 0,
        "WorldImagery": 0,
        "Terrain": 0,
        "Voyager": 0,
        "OpenTopoMap": 0
    }
}
    """,
    "isBase64Encoded": False,
}
print(lambda_handler(payload, {}))