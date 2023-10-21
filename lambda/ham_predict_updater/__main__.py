from . import *
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
    
http.client.HTTPSConnection = MockHTTPS

logging.basicConfig(
    format="%(asctime)s %(levelname)s:%(message)s", level=logging.DEBUG
)

class TestAmateurPrediction(unittest.TestCase):
    def setUp(self):
        es.request = MagicMock(side_effect=mock_es_request)
        client.connect = MagicMock()
        client.loop_start = MagicMock()
        client.username_pw_set = MagicMock()
        client.tls_set = MagicMock()
        client.publish = MagicMock()
        on_connect(client, "userdata", "flags", 0)

    @patch("time.sleep")
    def test_float_prediction(self, MockSleep):
        predict({},{})
        date_prefix = datetime.now().strftime("%Y-%m")
        es.request.assert_has_calls(
            [
                call(json.dumps(test_values.flight_doc_search),"flight-doc/_search", "POST"),
                call(json.dumps(test_values.ham_telm_search), "ham-telm-*/_search", "GET"),
                call(test_values.es_bulk_upload,f"ham-predictions-{date_prefix}/_bulk","POST")
            ]
        )
        client.username_pw_set.assert_called()
        client.loop_start.assert_called()
        client.connect.assert_called()
        client.publish.assert_has_calls([test_values.mqtt_publish_call])
        time.sleep.assert_called_with(0.5) # make sure we sleep to let paho mqtt queue clear

if __name__ == '__main__':
    unittest.main()
