from . import *
import base64

import zlib

# response = get_telem(
#         {
#             "queryStringParameters":{
#             #    "payload_callsign": "HORUS-V2",
#                "duration": "3d"
#             }
#         }, {})

response = get_listener_telemetry(
        {
            "queryStringParameters":{
            #    "payload_callsign": "HORUS-V2",
               "duration": "3h"
            }
        }, {})
compressed = base64.b64decode(response['body'])

decompressed = (zlib.decompress(compressed, 16 + zlib.MAX_WBITS))
print(json.loads(decompressed)
)
print(len(json.dumps(response)))