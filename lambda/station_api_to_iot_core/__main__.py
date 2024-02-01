import unittest
import station_api_to_iot_core
from unittest.mock import MagicMock, call, patch
import datetime
import copy
import json

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
    {"software_name": "radiosonde_auto_rx", "software_version": "1.5.8-beta2", "uploader_callsign": "A", "uploader_position": [null,null,null], "uploader_antenna": "Dipole", "uploader_contact_email": "none@none.com", "mobile": false}
    """,
    "isBase64Encoded": False,
}

class TestStation(unittest.TestCase):
    def setUp(self):
        station_api_to_iot_core.es.request = MagicMock()
        station_api_to_iot_core.sns.publish = MagicMock()
    
    @patch('builtins.print')
    def test_blocked_call(self, mocked_print):
        blocked_call_payload = copy.deepcopy(payload)
        body = json.loads(blocked_call_payload["body"])
        body["uploader_callsign"] = "CHANGEME_RDZTTGO"
        blocked_call_payload["body"] = json.dumps(body)
        station_api_to_iot_core.lambda_handler(blocked_call_payload,{})
        station_api_to_iot_core.es.request.assert_not_called()
        station_api_to_iot_core.sns.publish.assert_not_called()
        mocked_print.assert_called()
        json.loads(mocked_print.call_args.args[0])

    @patch('builtins.print')
    def test_call(self, mocked_print):
        blocked_call_payload = copy.deepcopy(payload)
        body = json.loads(blocked_call_payload["body"])
        blocked_call_payload["body"] = json.dumps(body)
        station_api_to_iot_core.lambda_handler(blocked_call_payload,{})
        station_api_to_iot_core.es.request.assert_called()
        station_api_to_iot_core.sns.publish.assert_called()
if __name__ == '__main__':
    unittest.main()
