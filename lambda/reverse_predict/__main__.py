from . import *
# print(get_sondes({"queryStringParameters":{"lat":"-28.22717","lon":"153.82996","distance":"50000"}}, {}))
# mode: 6hours
# type: positions
# format: json
# max_positions: 0
# position_id: 0
# vehicles: RS_*;*chase
print(predict(
        {"queryStringParameters": {
            "vehicles": ""
        }}, {}
        ))


# get list of sondes,    serial, lat,lon, alt
#           and        current rate
# for each one, request http://predict.cusf.co.uk/api/v1/?launch_latitude=-37.8136&launch_longitude=144.9631&launch_datetime=2021-02-22T00:15:18.513413Z&launch_altitude=30000&ascent_rate=5&burst_altitude=30000.1&descent_rate=5
# have to set the burst alt slightly higher than the launch