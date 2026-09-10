import recovered
import logging
import json
from datetime import datetime
import time
import unittest
from unittest.mock import MagicMock, call, patch

# Mock OpenSearch requests
def mock_es_request(body, path, method):
    if path == "telm-*/_search":
        return {
            "aggregations":{
                "1": {
                    "hits": {
                        "hits": [1]
                    }
                }
            }
        }
    return {
        "took": 24,
        "timed_out": False,
        "_shards": {
            "total": 1,
            "successful": 1,
            "skipped": 0,
            "failed": 0
        },
        "hits": {
            "total": {
            "value": 10000,
            "relation": "gte"
            },
            "max_score": None,
            "hits": [
            {
                "_index": "recovered",
                "_id": "RdGxiqABONgEZ5vsECCz",
                "_score": None,
                "_source": {
                "serial": "X3642102",
                "lat": 55.79124,
                "lon": 9.87254,
                "alt": 0,
                "recovered": True,
                "planned": False,
                "recovered_by": "DanLund",
                "description": "Fundet i en gruppe træer.",
                "recovery_software": "Sondehub Tracker",
                "datetime": "2026-09-10T09:40:54.647694+00:00",
                "position": [
                    9.87254,
                    55.79124
                ]
                },
                "sort": [
                1789033254647
                ]
            },
            {
                "_index": "recovered",
                "_id": "xM-fiqABONgEZ5vsR7Yw",
                "_score": None,
                "_source": {
                "serial": "X3642102",
                "lat": 55.7889,
                "lon": 9.8738,
                "alt": 0,
                "recovered": True,
                "planned": False,
                "recovered_by": "DanLund",
                "description": "Latest",
                "recovery_software": "Sondehub Tracker",
                "datetime": "2027-09-10T09:21:29.023800+00:00",
                "position": [
                    9.8738,
                    55.7889
                ]
                },
                "sort": [
                1789032089023
                ]
            },
            {
                "_index": "recovered",
                "_id": "4s-aiqABONgEZ5vsgFkH",
                "_score": None,
                "_source": {
                "recovery_software": "sondehub.org/found",
                "serial": "X3642102",
                "lat": 53.62814,
                "lon": 27.88079,
                "alt": 222.8,
                "recovered": True,
                "planned": False,
                "recovered_by": "Владислав",
                "description": "",
                "datetime": "2026-09-10T09:16:14.717372+00:00",
                "position": [
                    27.88079,
                    53.62814
                ]
                },
                "sort": [
                1789031774717
                ]
            }
            ]
        }
    }
    # if path.endswith("_bulk"): # handle when the upload happens
    #     return {}
    # elif(path == "flight-doc/_search"): # handle flightdoc queries
    #     return mock_values.flight_docs
    # elif(path == "ham-telm-*/_search"): # handle telm searches
    #     return mock_values.ham_telm
    # else:
    #     raise NotImplemented

logging.basicConfig(
    format="%(asctime)s %(levelname)s:%(message)s", level=logging.DEBUG
)

class TestRecovered(unittest.TestCase):
    def setUp(self):
        recovered.es.request = MagicMock(side_effect=mock_es_request)
        recovered.client = MagicMock()
        recovered.client.connect = MagicMock()
        recovered.client.loop_start = MagicMock()
        recovered.client.username_pw_set = MagicMock()
        recovered.client.tls_set = MagicMock()
        recovered.client.publish = MagicMock()
        def mock_config(a,b,default=""):
            if b=="PORT":
                return 1234
            else:
                return "test"
        recovered.config_handler.get = mock_config
        recovered.on_connect(recovered.client, "userdata", "flags", 0)
    def tearDown(self): # reset some of the globals that get updated
        recovered.setup = False
        recovered.connected_flag = False

    def test_get_recovered(self):
        returned_recovered = recovered.get({},{})
        body_recovered = json.loads(returned_recovered['body'])
        self.assertEqual(returned_recovered['statusCode'], 200)
        self.assertEqual(len(body_recovered),1)
        self.assertEqual(body_recovered[0]['description'],'Latest')
        breakpoint()
    @patch("time.sleep")
    def test_recovered(self, MockSleep):
        r_payload = {
            "datetime": "2021-06-06T01:10:07.629Z",
            "serial": "S00000000",
            "lat": 0,
            "lon": 0,
            "alt": 0,
            "recovered": True,
            "recovered_by": "string",
            "description": "string"
        }
        recovered.put({
            "version": "2.0",
            "routeKey": "PUT /recovered",
            "rawPath": "/recovered",
            "rawQueryString": "",
            "queryStringParameters": {
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
    "body": json.dumps(r_payload),
    "isBase64Encoded": False,
},{})

        recovered.client.username_pw_set.assert_called()
        recovered.client.loop_start.assert_called()
        recovered.client.connect.assert_called()
        recovered.client.publish.assert_called()
        c_payload = r_payload
        c_payload["position"] = [
            float(r_payload['lat']),float(r_payload['lon'])
        ]
        recovered.client.publish.assert_has_calls([
            call(
                topic="recovery/S00000000",
                payload=json.dumps(r_payload),
                qos=0,
                retain=False
            )
        ])
        time.sleep.assert_called_with(0.3) # make sure we sleep to let paho mqtt queue clear
    
if __name__ == '__main__':
    unittest.main()
