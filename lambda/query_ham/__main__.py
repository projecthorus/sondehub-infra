from . import *
import base64

import zlib

response = get_telem_full(
        {
            "pathParameters": {
                "payload_callsign": "PD3EGE"
            },
            "queryStringParameters":{
              #  "payload_callsign" : "NOB14,VE6AGD-11",
                "last": "22269",
               "datetime": "1688655220.471",
              #  "format": "kml"
              #"duration": "732d"
            }
        }, {})
print(len(response['body']))
compressed = base64.b64decode(response['body'])

decompressed = (zlib.decompress(compressed, 16 + zlib.MAX_WBITS))
#print(json.loads(decompressed))
#print(decompressed.decode().splitlines()[:5])
print(decompressed.decode())