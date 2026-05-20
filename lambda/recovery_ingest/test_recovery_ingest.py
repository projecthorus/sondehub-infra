import recovery_ingest
import json
import unittest
from unittest.mock import patch, MagicMock
from io import StringIO

radiosondy_response = {
    "status": "200_OK",
    "results": [
        {
            "radiosonde": {
                "number": "X1234567",
                "alternative_number": "",
                "type": "RS41",
                "aux": "NO",
                "qrg": "400.50",
                "start_place": "MEOW"
            },
            "log_info": {
                "status": "FOUND",
                "finder": "meow-finder",
                "added_by": "meow-addedby",
                "log_added": "2026-05-20 01:50:46",
                "comment": "MEOW",
                "found_coordinates": {
                    "latitude": 0,
                    "longitude": 0
                }
            },
            "start_time": "2026-05-19 23:50:20",
            "nearest_city": "MEOW"
        }
    ]
}

sondehub_check_non_existing = []

class TestRecoveryIngest(unittest.TestCase):
    def setUp(self):

        def mock_config(a,b,default=""):
            return "meow"
        recovery_ingest.config_handler.get = mock_config

    @patch('urllib.request.urlopen')
    def test_handler(self, urlopen):
        cm = MagicMock()
        cm.getcode.return_value = 200
        cm.read.side_effect = [
            json.dumps(radiosondy_response),
            json.dumps(sondehub_check_non_existing),
            b"uploaded"
        ]
        urlopen.return_value = cm


        with unittest.mock.patch('sys.stdout', new = StringIO()): # hide stdout
            recovery_ingest.handler({},{})

        self.assertEqual(urlopen.call_count, 3)

    @patch('traceback.print_exc')
    @patch('urllib.request.urlopen')
    def test_handler_new_time_format(self, urlopen, tb):
        cm = MagicMock()
        cm.getcode.return_value = 200
        radiosondy_response["results"][0]["start_time"] = "2026-05-19T23:50:20Z"
        radiosondy_response["results"][0]["log_info"]["log_added"] = "2026-05-19T23:50:20Z"
        cm.read.side_effect = [
            json.dumps(radiosondy_response),
            json.dumps(sondehub_check_non_existing),
            b"uploaded"
        ]
        urlopen.return_value = cm

        with unittest.mock.patch('sys.stdout', new = StringIO()): # hide stdout
            recovery_ingest.handler({},{})

        self.assertEqual(urlopen.call_count, 3)
        tb.assert_not_called()