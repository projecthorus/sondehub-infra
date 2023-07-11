from . import *

#print(get_listener_telemetry({"queryStringParameters":{}}, {}))
# print(telm_stats({
#     "version": "2.0",
#     "routeKey": "GET /sondes",
#     "rawPath": "/sondes",
#     "rawQueryString": "lat=49.827648&lon=6.106842&distance=400000&last=-60",
#     "headers": {
#         "cache-control": "no-cache",
#         "content-length": "0",
#         "host": "api-raw.v2.sondehub.org",
#         "user-agent": "Amazon CloudFront",
#         "via": "1.1 ee4db0d243ceb0d1993e5f46ad6c0f01.cloudfront.net (CloudFront)",
#         "x-amz-cf-id": "KF68O6r-OP5oTosFLdix7-RWM6xeW08ZF48fgvwLkj9f3s4fJuCFKg==",
#         "x-amzn-trace-id": "Root=1-61d14df5-0f9dbfe563e89f170e65a3bf",
#         "x-forwarded-for": "94.252.35.58, 64.252.86.150",
#         "x-forwarded-port": "443",
#         "x-forwarded-proto": "https"
#     },
#     "queryStringParameters": {
#         "distance": "400000",
#         "last": "-60",
#         "lat": "49.827648",
#         "lon": "6.106842"
#     },
#     "requestContext": {
#         "accountId": "143841941773",
#         "apiId": "r03szwwq41",
#         "domainName": "api-raw.v2.sondehub.org",
#         "domainPrefix": "api-raw",
#         "http": {
#             "method": "GET",
#             "path": "/sondes",
#             "protocol": "HTTP/1.1",
#             "sourceIp": "94.252.35.58",
#             "userAgent": "Amazon CloudFront"
#         },
#         "requestId": "LTkeXjgXIAMEVzw=",
#         "routeKey": "GET /sondes",
#         "stage": "$default",
#         "time": "02/Jan/2022:07:02:13 +0000",
#         "timeEpoch": 1641106933368
#     },
#     "isBase64Encoded": False
# }, None))
# mode: 6hours
# type: positions
# format: json
# max_positions: 0
# position_id: 0
# vehicles: RS_*;*chase
#     print(
#         datanew(
#             {
#              "queryStringParameters": {
# "mode": "single",
# "format": "json",
# "position_id": "S1443103-2021-07-20T12:46:19.040000Z"
#              }
#             },
#             {},
#         )
#     )
# print(get_sites({"queryStringParameters":{"station":-1}},{}))

print(get_telem(
    {
        "queryStringParameters": {
            "duration": "3h",
            # "serial": "S4430086"
        }},{}
))
# b=get_telem(
#     {
#         "queryStringParameters": {
#             "duration": "3h",
#             "serial": "5C3A7D72"
#         }},{}
    
#     )
# print (
#     get_chase(
#         {"queryStringParameters": {
#             "duration": "1d"
#             }
#         },
#         {}
#     )
# )


# print(
#     datanew(
#         {
#          "queryStringParameters": {
#              "type": "positions",
#              "mode": "3hours",
#              "position_id": "0"
#          }
#         },
#         {},
#     )
# )
# print(
#     get_telem(
#         {
#             "queryStringParameters":{
#                 # "serial": "S3210639",
#                 "duration": "3h",
#                # "datetime": "2021-07-26T06:49:29.001000Z"
#             }
#         }, {}
#     )
# )
