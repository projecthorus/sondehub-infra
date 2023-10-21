import ham_predict_updater
import logging
import json
from datetime import datetime
import time
from . import mock_values, test_values
import unittest
from unittest.mock import MagicMock, call, patch

# Mock OpenSearch requests
def mock_es_request(body, path, method):
    if path.endswith("_bulk"): # handle when the upload happens
        return {}
    elif(path == "flight-doc/_search"): # handle flightdoc queries
        return mock_values.flight_docs
    elif(path == "ham-telm-*/_search"): # handle telm searches
        return mock_values.ham_telm
    else:
        raise NotImplemented

# Mock out tawhiri
class MockResponse(object):
    code = 200
    def read(self):
        return mock_values.tawhiri_respose # currently we only mock a float profile
    
class MockHTTPS(object):
    logging.debug(object)
    def __init__(self, url):
        logging.debug(url)
    def request(self,method, url):
        pass
    def getresponse(self):
        return MockResponse()
    
ham_predict_updater.http.client.HTTPSConnection = MockHTTPS

logging.basicConfig(
    format="%(asctime)s %(levelname)s:%(message)s", level=logging.DEBUG
)

class TestAmateurPrediction(unittest.TestCase):
    def setUp(self):
        ham_predict_updater.es.request = MagicMock(side_effect=mock_es_request)
        ham_predict_updater.client.connect = MagicMock()
        ham_predict_updater.client.loop_start = MagicMock()
        ham_predict_updater.client.username_pw_set = MagicMock()
        ham_predict_updater.client.tls_set = MagicMock()
        ham_predict_updater.client.publish = MagicMock()
        ham_predict_updater.on_connect(ham_predict_updater.client, "userdata", "flags", 0)
    def tearDown(self): # reset some of the globals that get updated
        ham_predict_updater.client = ham_predict_updater.mqtt.Client(transport="websockets")
        ham_predict_updater.setup = False
        ham_predict_updater.connected_flag = False


    @patch("time.sleep")
    def test_float_prediction(self, MockSleep):
        ham_predict_updater.predict({},{})
        date_prefix = datetime.now().strftime("%Y-%m")
        ham_predict_updater.es.request.assert_has_calls(
            [
                call(json.dumps(test_values.flight_doc_search),"flight-doc/_search", "POST"),
                call(json.dumps(test_values.ham_telm_search), "ham-telm-*/_search", "GET"),
                call(test_values.es_bulk_upload,f"ham-predictions-{date_prefix}/_bulk","POST")
            ]
        )
        ham_predict_updater.client.username_pw_set.assert_called()
        ham_predict_updater.client.loop_start.assert_called()
        ham_predict_updater.client.connect.assert_called()
        ham_predict_updater.client.publish.assert_has_calls([test_values.mqtt_publish_call])
        time.sleep.assert_called_with(0.5) # make sure we sleep to let paho mqtt queue clear
    
    @patch('ham_predict_updater.connect')
    def test_connect_only_called_once(self, mock_connect):
        ham_predict_updater.predict({},{})
        ham_predict_updater.predict({},{})
        mock_connect.assert_called_once()

if __name__ == '__main__':
    unittest.main()
