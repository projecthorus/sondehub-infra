from . import *

print(handler({
  "Records": [
    {
      "cf": {
        "config": {
          "distributionId": "EXAMPLE"
        },
        "request": {
          "uri": "/MRZ-S1234",
          "querystring": "auth=test&foo=bar",
          "method": "GET",
          "clientIp": "2001:cdba::3257:9652",
          "headers": {
            "host": [
              {
                "key": "Host",
                "value": "d123.cf.net"
              }
            ],
            "user-agent": [
              {
                "key": "User-Agent",
                "value": "Test Agent"
              }
            ],
            "user-name": [
              {
                "key": "User-Name",
                "value": "aws-cloudfront"
              }
            ]
          }
        }
      }
    }
  ]
}, None))