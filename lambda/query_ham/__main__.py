from . import *
import base64

import zlib

response = get_telem_full(
        {
            "pathParameters": {
                "payload_callsign" : "HORUS-V2"
            },
            "queryStringParameters":{
                "last": "3600",
                "datetime": "2022-05-07T04:18:10.000000Z",
                "format": "csv"
            }
        }, {})
print(len(response['body']))
compressed = base64.b64decode(response['body'])

decompressed = (zlib.decompress(compressed, 16 + zlib.MAX_WBITS))
#print(json.loads(decompressed))
print(decompressed.decode().splitlines()[:5])