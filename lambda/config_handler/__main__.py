import config_handler

import unittest
from unittest.mock import MagicMock, call, patch

# Mock AWS API calls
secret_call = {
                'ARN': 'arn:aws:secretsmanager:us-west-2:123456789012:secret:MyTestDatabaseSecret-a1b2c3',
                'CreatedDate': 1523477145.713,
                'Name': 'MyTestDatabaseSecret',
                'SecretString': '{\n  "PASSWORD":"test_password"\n}\n',
                'VersionId': 'EXAMPLE1-90ab-cdef-fedc-ba987SECRET1',
                'VersionStages': [
                    'AWSCURRENT',
                ],
                'ResponseMetadata': {
                    '...': '...',
                },
            }

class TestConfigHandler(unittest.TestCase):
    def test_env(self):
        with patch.dict(config_handler.os.environ,{ "MQTT_PASSWORD": "test_password" }, clear=True):
            return_value = config_handler.get("MQTT", "PASSWORD")
        self.assertEqual(return_value, "test_password")

    @patch('botocore.client.BaseClient._make_api_call', return_value=secret_call)
    def test_sm(self, MockApiCall):
        with patch.dict(config_handler.os.environ,{}, clear=True): #ensure that local env variables don't influence the tests
            return_value = config_handler.get("MQTT", "PASSWORD")
        MockApiCall.assert_called()
        self.assertEqual(return_value, "test_password")

    @patch('botocore.client.BaseClient._make_api_call', return_value=secret_call)
    def test_not_found(self, MockApiCall):
        with patch.dict(config_handler.os.environ,{}, clear=True):
            self.assertRaises(KeyError, config_handler.get, "MQTT", "NOTPASSWORD")
    
    def test_default(self):
        with patch.dict(config_handler.os.environ,{}, clear=True):
            return_value = config_handler.get("MQTT", "PASSWORD", "test_password_abc")
        self.assertEqual(return_value, "test_password_abc")
      
if __name__ == '__main__':
    unittest.main()
