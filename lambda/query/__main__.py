from . import *

#print(get_sondes({"queryStringParameters":{"lat":"-32.7933","lon":"151.8358","distance":"5000", "last":"604800"}}, {}))
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
#  print(get_sites({},{}))
print(
    get_telem(
        {
            "queryStringParameters": {
                "duration": "1d",
                # "serial": "S4430086"
            }},{}
        
        )
    )
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
