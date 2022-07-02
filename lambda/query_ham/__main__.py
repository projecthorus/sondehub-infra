from . import *
import base64

import zlib

response = get_telem_full(
        {
            "pathParameters": {
                "payload_callsign" : "HORUSBINARY"
            },
            "queryStringParameters":{
                "last": "10800",
                "datetime": "2022-06-26T08:30:00.000001Z",
                "format": "kml"
            }
        }, {})
print(len(response['body']))
compressed = base64.b64decode(response['body'])

decompressed = (zlib.decompress(compressed, 16 + zlib.MAX_WBITS))
#print(json.loads(decompressed))
#print(decompressed.decode().splitlines()[:5])
print(decompressed.decode())