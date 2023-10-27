from . import *


import unittest
from unittest.mock import MagicMock

# mock out context
class fakeContext:
    def __init__(self):
        self.log_stream_name = str(uuid.uuid4())

import json
import base64
import gzip
import uuid
import datetime
import copy

example_body = [{
    "software_name": "SondeHubUploader", 
    "software_version": "1.0.0", 
    "uploader_callsign": "a", 
    "uploader_position": [53.23764, 7.74426, 7.0], 
    "uploader_antenna": "5/8-Wave-J-Pole",
    "time_received": "2023-01-22T22:48:43.208780Z",
    "datetime": "2023-06-13T00:48:41.000000Z",
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

def compress_payload(payload):
    compressed = BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode='w') as f:
        f.write(json.dumps(payload).encode('utf-8'))
    compressed.seek(0)
    bbody = base64.b64encode(compressed.read()).decode("utf-8")
    output = {
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
    return output

logs.put_log_events = MagicMock(return_value={'nextSequenceToken':1})
logs.create_log_stream = MagicMock(return_value={'nextSequenceToken':1})

class TestIngestion(unittest.TestCase):
    def setUp(self):
        sns.publish = MagicMock() # we reset the mock for every time so we can assert correctly if its called - this won't work when doing parallel testing
    def test_report_time_too_late(self):
        payload = copy.deepcopy(example_body)
        output = lambda_handler(compress_payload(payload), fakeContext())
        sns.publish.assert_not_called()
        body_decode = json.loads(output["body"])
        self.assertEqual(body_decode["message"], "some or all payloads could not be processed")
        self.assertEqual(body_decode["errors"][0]["error_message"],"Sonde reported time too far from current UTC time. Either sonde time or system time is invalid. (Threshold: 48 hours)")
    def test_good_payload(self):
        payload = copy.deepcopy(example_body)
        payload[0]["datetime"] = datetime.datetime.now().isoformat()
        output = lambda_handler(compress_payload(payload), fakeContext())
        sns.publish.assert_called()
        self.assertEqual(output["body"], "^v^ telm logged")
        self.assertEqual(output["statusCode"], 200)

    def test_good_ttgo_devel_payload(self):
        payload = copy.deepcopy(example_body)
        payload[0]["datetime"] = datetime.datetime.now().isoformat()
        payload[0]["software_name"] = "rdzTTGOsonde" 
        payload[0]["software_version"] = "devel20230829"
        payload[0]["type"] = "DFM"
        output = lambda_handler(compress_payload(payload), fakeContext())
        sns.publish.assert_called()
        self.assertEqual(output["body"], "^v^ telm logged")
        self.assertEqual(output["statusCode"], 200)

    def test_good_ttgo_master_payload(self):
        payload = copy.deepcopy(example_body)
        payload[0]["datetime"] = datetime.datetime.now().isoformat()
        payload[0]["software_name"] = "rdzTTGOsonde" 
        payload[0]["software_version"] = "master_v0.9.3"
        payload[0]["type"] = "DFM"
        output = lambda_handler(compress_payload(payload), fakeContext())
        sns.publish.assert_called()
        self.assertEqual(output["body"], "^v^ telm logged")
        self.assertEqual(output["statusCode"], 200)
    def test_bad_ttgo_devel_payload(self):
        payload = copy.deepcopy(example_body)
        payload[0]["datetime"] = datetime.datetime.now().isoformat()
        payload[0]["software_name"] = "rdzTTGOsonde" 
        payload[0]["software_version"] = "devel20230104"
        payload[0]["type"] = "DFM"
        output = lambda_handler(compress_payload(payload), fakeContext())
        sns.publish.assert_not_called()
        body_decode = json.loads(output["body"])
        self.assertEqual(body_decode["message"], "some or all payloads could not be processed")

    def test_bad_ttgo_master_payload(self):
        payload = copy.deepcopy(example_body)
        payload[0]["datetime"] = datetime.datetime.now().isoformat()
        payload[0]["software_name"] = "rdzTTGOsonde" 
        payload[0]["software_version"] = "master_v0.9.2"
        payload[0]["type"] = "DFM"
        output = lambda_handler(compress_payload(payload), fakeContext())
        sns.publish.assert_not_called()
        body_decode = json.loads(output["body"])
        self.assertEqual(body_decode["message"], "some or all payloads could not be processed")
    def test_weird_ttgo_branch_payload(self):
        payload = copy.deepcopy(example_body)
        payload[0]["datetime"] = datetime.datetime.now().isoformat()
        payload[0]["software_name"] = "rdzTTGOsonde" 
        payload[0]["software_version"] = "multich_v3"
        payload[0]["type"] = "DFM"
        output = lambda_handler(compress_payload(payload), fakeContext())
        sns.publish.assert_not_called()
        body_decode = json.loads(output["body"])
        self.assertEqual(body_decode["message"], "some or all payloads could not be processed")
    def test_good_dxlaprsshue_payload(self):
        payload = copy.deepcopy(example_body)
        payload[0]["datetime"] = datetime.datetime.now().isoformat()
        payload[0]["software_name"] = "dxlAPRS-SHUE" 
        payload[0]["software_version"] = "1.1.2"
        payload[0]["type"] = "M10"
        output = lambda_handler(compress_payload(payload), fakeContext())
        sns.publish.assert_called()
        self.assertEqual(output["body"], "^v^ telm logged")
        self.assertEqual(output["statusCode"], 200)
    def test_bad_dxlaprsshue_payload(self):
        payload = copy.deepcopy(example_body)
        payload[0]["datetime"] = datetime.datetime.now().isoformat()
        payload[0]["software_name"] = "dxlAPRS-SHUE" 
        payload[0]["software_version"] = "1.0.2"
        payload[0]["type"] = "M10"
        output = lambda_handler(compress_payload(payload), fakeContext())
        sns.publish.assert_not_called()
        body_decode = json.loads(output["body"])
        self.assertEqual(body_decode["message"], "some or all payloads could not be processed")
    def test_good_sondemonitor_payload(self):
        payload = copy.deepcopy(example_body)
        payload[0]["datetime"] = datetime.datetime.now().isoformat()
        payload[0]["software_name"] = "SondeMonitor" 
        payload[0]["software_version"] = "6.2.8.8"
        payload[0]["type"] = "DFM"
        output = lambda_handler(compress_payload(payload), fakeContext())
        sns.publish.assert_called()
        self.assertEqual(output["body"], "^v^ telm logged")
        self.assertEqual(output["statusCode"], 200)
    def test_bad_sondemonitor_payload(self):
        payload = copy.deepcopy(example_body)
        payload[0]["datetime"] = datetime.datetime.now().isoformat()
        payload[0]["software_name"] = "SondeMonitor" 
        payload[0]["software_version"] = "6.2.8.7"
        payload[0]["type"] = "DFM"
        output = lambda_handler(compress_payload(payload), fakeContext())
        sns.publish.assert_not_called()
        body_decode = json.loads(output["body"])
        self.assertEqual(body_decode["message"], "some or all payloads could not be processed")

if __name__ == '__main__':
    unittest.main()