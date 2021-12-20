from . import *

# Predictor test
# conn = http.client.HTTPSConnection("tawhiri.v2.sondehub.org")
# _now = datetime.utcnow().isoformat() + "Z"

# _ascent = get_standard_prediction(conn, _now, -34.0, 138.0, 10.0, burst_altitude=26000)
# print(f"Got {len(_ascent)} data points for ascent prediction.")
# _descent = get_standard_prediction(conn, _now, -34.0, 138.0, 24000.0, burst_altitude=24000.5)
# print(f"Got {len(_descent)} data points for descent prediction.")

# test = predict(
#       {},{}
#     )
#print(get_launch_sites())
#print(get_reverse_predictions())
# for _serial in test:
#     print(f"{_serial['serial']}: {len(_serial['data'])}")


logging.basicConfig(
    format="%(asctime)s %(levelname)s:%(message)s", level=logging.DEBUG
)

print(predict(
        {},{}
    ))
# bulk_upload_es("reverse-prediction",[{
#       "datetime" : "2021-10-04",
#       "data" : { },
#       "serial" : "R12341234",
#       "station" : "-2",
#       "subtype" : "RS41-SGM",
#       "ascent_rate" : "5",
#       "alt" : 1000,
#       "position" : [
#         1,
#         2
#       ],
#       "type" : "RS41"
#     }]
# )

