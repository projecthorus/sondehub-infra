from . import *
import zlib
import pprint
import json
import base64

output = get({"queryStringParameters":{
    "lat":"-37.8136",
    "lon": "144.9631",
    "distance":"100000",
    "from": "2025-11-03T23:02:29.644421",
    "to": "2025-11-06T23:02:29.644421",
    "limit": 200
    }},{})


# output = get({"queryStringParameters":{
#     "from": "2026-11-03T12:02:29.644421",
#     "to": "2026-11-03T23:02:29.644421",
#     "limit": 200
#     }},{})


print(zlib.decompress(base64.b64decode(output['body']), 16 + zlib.MAX_WBITS).decode())

#get({"queryStringParameters":{"serial":"V4620982"}},{})

# get({"queryStringParameters":{
#     "launchsite": "71811",
#     "limit": 10
# }},{})

# get({"queryStringParameters":{
#     "lat":"-37.66493531029459",
#     "lon": "145.93896300086087",
#     "distance":"10",
#     "from": "2025-11-03T23:02:29.644421",
#     "to": "2025-11-06T23:02:29.644421",
#     "limit": 1
#     }},{})
