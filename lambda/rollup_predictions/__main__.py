from . import *
# print(handler(
#        {
#     "Records": [
#         {
#             "messageId": "3b5853b3-369c-40bf-8746-130c918fbb5c",
#             "receiptHandle": "AQEBg+/MIA2rSNmlrpXvk7pbi26kgIzqhairaHWGSpMgLzf2T54PLUmG+eG6CDOv35e42scDH0gppmS9RTQVu8D161oHYohhd1+0S4LtFJdgXr3At86NBIky5+y1A/wVuUm1FNQSvGKIDRgBhCgcCzLkEMNYIWWeDmg2ez2SCPu/3hmY5sc7eC32uqz5es9PspgQXOTykmoNv/q37iy2RBRDdu51Tq7yIxEr+Us3qkQrddAJ7qsA0l09aRL+/PJe1V/7MMN3CFyBATpRP/G3Gjn0Iuu4i2UhkRx2pF+0Hj8yhhHbqTMcw5sbbGIWMdsMXFQKUCHNx6HPkbuwIWo0TsINQjY7IXeZM/mNq65xC4avSlctJ/9BMzOBtFwbnRPZfHmlS5Al2nF1Vu3RecFGbTm1nQ==",
#             "body": "R5130039",
#             "attributes": {
#                 "ApproximateReceiveCount": "1",
#                 "SentTimestamp": "1627873604999",
#                 "SenderId": "AROASC7NF3EG5DNHEPSYZ:queue_data_update",
#                 "ApproximateFirstReceiveTimestamp": "1627873751266"
#             },
#             "messageAttributes": {},
#             "md5OfBody": "b3d67879b6a2e7f3abd62d404e53f71f",
#             "md5OfMessageAttributes": None,
#             "eventSource": "aws:sqs",
#             "eventSourceARN": "arn:aws:sqs:us-east-1:143841941773:update-history",
#             "awsRegion": "us-east-1"
#         }
#     ]
# }, {}))

def find_indexes():

    response = es.request("",
                           "_cat/indices/predictions-2024*,-predictions-*-rollup?format=json",
                           "GET")
    return [x['index'] for x in response]
    print(response)

indexes = find_indexes()
for index in indexes:
    print(f"Doing rollup {index}")
    fetch_es(index+"/_search")
    serials = {}
