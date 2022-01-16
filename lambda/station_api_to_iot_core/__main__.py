from . import *
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
    {"software_name": "radiosonde_auto_rx", "software_version": "1.5.8-beta2", "uploader_callsign": "CHANGEME_RDZTTGO", "uploader_position": [null,null,null], "uploader_antenna": "Dipole", "uploader_contact_email": "none@none.com", "mobile": false}
    """,
    "isBase64Encoded": False,
}
print(lambda_handler(payload, {}))