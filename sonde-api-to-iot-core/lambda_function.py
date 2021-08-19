import sys
import json
import boto3
import zlib
import base64
import datetime
import functools
from email.utils import parsedate
import os
import re
from math import radians, degrees, sin, cos, atan2, sqrt, pi


# todo
# we should add some value checking
# we typically perform version banning here based on user agent
# error handling - at the moment we bail on a single failure
# report to the user what's happened

# Earthmaths code by Daniel Richman (thanks!)
# Copyright 2012 (C) Daniel Richman; GNU GPL 3
def position_info(listener, balloon):
    """
    Calculate and return information from 2 (lat, lon, alt) tuples
    Returns a dict with:
     - angle at centre
     - great circle distance
     - distance in a straight line
     - bearing (azimuth or initial course)
     - elevation (altitude)
    Input and output latitudes, longitudes, angles, bearings and elevations are
    in degrees, and input altitudes and output distances are in meters.
    """

    # Earth:
    radius = 6371000.0

    (lat1, lon1, alt1) = listener
    (lat2, lon2, alt2) = balloon

    lat1 = radians(lat1)
    lat2 = radians(lat2)
    lon1 = radians(lon1)
    lon2 = radians(lon2)

    # Calculate the bearing, the angle at the centre, and the great circle
    # distance using Vincenty's_formulae with f = 0 (a sphere). See
    # http://en.wikipedia.org/wiki/Great_circle_distance#Formulas and
    # http://en.wikipedia.org/wiki/Great-circle_navigation and
    # http://en.wikipedia.org/wiki/Vincenty%27s_formulae
    d_lon = lon2 - lon1
    sa = cos(lat2) * sin(d_lon)
    sb = (cos(lat1) * sin(lat2)) - (sin(lat1) * cos(lat2) * cos(d_lon))
    bearing = atan2(sa, sb)
    aa = sqrt((sa ** 2) + (sb ** 2))
    ab = (sin(lat1) * sin(lat2)) + (cos(lat1) * cos(lat2) * cos(d_lon))
    angle_at_centre = atan2(aa, ab)
    great_circle_distance = angle_at_centre * radius

    # Armed with the angle at the centre, calculating the remaining items
    # is a simple 2D triangley circley problem:

    # Use the triangle with sides (r + alt1), (r + alt2), distance in a
    # straight line. The angle between (r + alt1) and (r + alt2) is the
    # angle at the centre. The angle between distance in a straight line and
    # (r + alt1) is the elevation plus pi/2.

    # Use sum of angle in a triangle to express the third angle in terms
    # of the other two. Use sine rule on sides (r + alt1) and (r + alt2),
    # expand with compound angle formulae and solve for tan elevation by
    # dividing both sides by cos elevation
    ta = radius + alt1
    tb = radius + alt2
    ea = (cos(angle_at_centre) * tb) - ta
    eb = sin(angle_at_centre) * tb
    elevation = atan2(ea, eb)

    # Use cosine rule to find unknown side.
    distance = sqrt((ta ** 2) + (tb ** 2) - 2 * tb * ta * cos(angle_at_centre))

    # Give a bearing in range 0 <= b < 2pi
    if bearing < 0:
        bearing += 2 * pi

    return {
        "listener": listener,
        "balloon": balloon,
        "listener_radians": (lat1, lon1, alt1),
        "balloon_radians": (lat2, lon2, alt2),
        "angle_at_centre": degrees(angle_at_centre),
        "angle_at_centre_radians": angle_at_centre,
        "bearing": degrees(bearing),
        "bearing_radians": bearing,
        "great_circle_distance": great_circle_distance,
        "straight_distance": distance,
        "elevation": degrees(elevation),
        "elevation_radians": elevation,
    }

# stolen from https://github.com/projecthorus/radiosonde_auto_rx/blob/master/auto_rx/auto_rx.py#L467
def telemetry_filter(telemetry):
    """Filter incoming radiosonde telemetry based on various factors,
        - Invalid Position
        - Invalid Altitude
        - Abnormal range from receiver.
        - Invalid serial number.
        - Abnormal date (more than 6 hours from utcnow)
    This function is defined within this script to avoid passing around large amounts of configuration data.
    """

    # First Check: zero lat/lon
    if (telemetry["lat"] == 0.0) and (telemetry["lon"] == 0.0):
        return (False,f"Zero Lat/Lon. Sonde { telemetry['serial']} does not have GPS lock.")

    max_altitude = 50000
    # Second check: Altitude cap.
    if telemetry["alt"] > max_altitude:
        _altitude_breach = telemetry["alt"] - max_altitude
        return (False,f"Sonde {telemetry['serial']} position breached altitude cap by {_altitude_breach}m.")

    # Third check: Number of satellites visible.
    if "sats" in telemetry:
        if telemetry["sats"] < 4: 
            return (False, f"Sonde {telemetry['serial']} can only see {telemetry['sats']} SVs - discarding position as bad.")

    max_radius = 1000
    # Fourth check - is the payload more than x km from our listening station.
    # Only run this check if a station location has been provided.
    if 'uploader_position' in telemetry and telemetry['uploader_position'] != None and telemetry['uploader_position'][0] != None and telemetry['uploader_position'][1] != None and telemetry['uploader_position'][2] != None and float(telemetry['uploader_position'][0]) != 0 and float(telemetry['uploader_position'][1]) != 0:
        # Calculate the distance from the station to the payload.
        _listener = (
            float(telemetry['uploader_position'][0]),
            float(telemetry['uploader_position'][1]),
            float(telemetry['uploader_position'][2])
        )
        _payload = (telemetry["lat"], telemetry["lon"], telemetry["alt"])
        # Calculate using positon_info function from rotator_utils.py
        _info = position_info(_listener, _payload)

        if _info["straight_distance"] > max_radius * 1000:
            _radius_breach = (
                _info["straight_distance"] / 1000.0 - max_radius
            )
            
            return (False, f"Sonde {telemetry['serial']} position breached radius cap by {_radius_breach:.1f} km.")

    # DateTime Check
    
    _delta_time = (
        datetime.datetime.now() - datetime.datetime.fromisoformat(telemetry["datetime"].replace("Z",""))
    ).total_seconds()

    sonde_time_threshold = 48
    if abs(_delta_time) > (3600 * sonde_time_threshold):
        return (False, f"Sonde reported time too far from current UTC time. Either sonde time or system time is invalid. (Threshold: {sonde_time_threshold} hours)")

    # Payload Serial Number Checks
    _serial = telemetry["serial"]
    # Run a Regex to match known Vaisala RS92/RS41 serial numbers (YWWDxxxx)
    # RS92: https://www.vaisala.com/sites/default/files/documents/Vaisala%20Radiosonde%20RS92%20Serial%20Number.pdf
    # RS41: https://www.vaisala.com/sites/default/files/documents/Vaisala%20Radiosonde%20RS41%20Serial%20Number.pdf
    # This will need to be re-evaluated if we're still using this code in 2021!
    # UPDATE: Had some confirmation that Vaisala will continue to use the alphanumeric numbering up until
    # ~2025-2030, so have expanded the regex to match (and also support some older RS92s)
    # Modified 2021-06 to be more flexible and match older sondes, and reprogrammed sondes.
    # Still needs a letter at the start, but the numbers don't need to match the format exactly.
    vaisala_callsign_valid = re.match(r"[C-Z][\d][\d][\d]\d{4}", _serial)

    # Just make sure we're not getting the 'xxxxxxxx' unknown serial from the DFM decoder.
    if "DFM" in telemetry["type"]:
        dfm_callsign_valid = "x" not in _serial
    else:
        dfm_callsign_valid = False

    # Check Meisei sonde callsigns for validity.
    # meisei_ims returns a callsign of IMS100-xxxxxx until it receives the serial number, so we filter based on the x's being present or not.
    if "MEISEI" in telemetry["type"]:
        meisei_callsign_valid = "x" not in _serial
    else:
        meisei_callsign_valid = False

    if "MRZ" in telemetry["type"]:
        mrz_callsign_valid = "x" not in _serial
    else:
        mrz_callsign_valid = False

    # If Vaisala or DFMs, check the callsigns are valid. If M10, iMet or LMS6, just pass it through - we get callsigns immediately and reliably from these.
    if (
        vaisala_callsign_valid
        or dfm_callsign_valid
        or meisei_callsign_valid
        or mrz_callsign_valid
        or ("M10" in telemetry["type"])
        or ("M20" in telemetry["type"])
        or ("LMS" in telemetry["type"])
        or ("iMet" in telemetry["type"])
    ):
        return (True, "")
    else:
        _id_msg = "Payload ID %s is invalid." % telemetry["serial"]
        # Add in a note about DFM sondes and their oddness...
        if "DFM" in telemetry["serial"]:
            _id_msg += " Note: DFM sondes may take a while to get an ID."

        if "MRZ" in telemetry["serial"]:
            _id_msg += " Note: MRZ sondes may take a while to get an ID."

        return (False, _id_msg)


def set_connection_header(request, operation_name, **kwargs):
    request.headers['Connection'] = 'keep-alive'

sns = boto3.client("sns",region_name="us-east-1")
sns.meta.events.register('request-created.sns', set_connection_header)

def post(payload):
    sns.publish(
                TopicArn=os.getenv("SNS_TOPIC"),
                Message=json.dumps(payload)
    )

def upload(event, context):
    if "isBase64Encoded" in event and event["isBase64Encoded"] == True:
        event["body"] = base64.b64decode(event["body"])
    if (
        "content-encoding" in event["headers"]
        and event["headers"]["content-encoding"] == "gzip"
    ):
        event["body"] = zlib.decompress(event["body"], 16 + zlib.MAX_WBITS)
    time_delta = None
    if "date" in event["headers"]:
        try:
            time_delta_header = event["headers"]["date"]
            time_delta = (
                datetime.datetime(*parsedate(time_delta_header)[:7])
                - datetime.datetime.utcnow()
            ).total_seconds()
        except:
            pass
    payloads = json.loads(event["body"])
    to_sns = []
    first = False
    errors = []
    for payload in payloads:
        if "user-agent" in event["headers"]:
            event["time_server"] = datetime.datetime.now().isoformat()
            payload["user-agent"] = event["headers"]["user-agent"]
        payload["position"] = f'{payload["lat"]},{payload["lon"]}'
        valid, error_message = telemetry_filter(payload)
        if not valid:
            errors.append({
                "error_message": error_message,
                "payload": payload
            })
        else:
            if time_delta:
                payload["upload_time_delta"] = time_delta
            if "uploader_position" in payload:
                if not payload["uploader_position"]:
                    payload.pop("uploader_position")
                else:
                    (payload["uploader_alt"], payload["uploader_position"]) = (
                        payload["uploader_position"][2],
                        f"{payload['uploader_position'][0]},{payload['uploader_position'][1]}",
                    )
            to_sns.append(payload)
    post(to_sns)
    return errors
def lambda_handler(event, context):
    errors = upload(event, context)
    error_message = {
        "message": "some or all payloads could not be processed",
        "errors": errors
    }
    if errors:
        print(json.dumps({"statusCode": 400, "body": error_message}))
        return {"statusCode": 400, "body": error_message}
    else:
        return {"statusCode": 200, "body": "^v^ telm logged"}

if __name__ == "__main__":
    payload = {
        "version": "2.0",
        "routeKey": "PUT /sondes/telemetry",
        "rawPath": "/sondes/telemetry",
        "rawQueryString": "",
        "headers": {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate",
            "content-encoding": "gzip",
            "content-length": "2135",
            "content-type": "application/json",
            "host": "api.v2.sondehub.org",
            "user-agent": "autorx-1.4.1-beta4",
            "x-amzn-trace-id": "Root=1-6015f571-6aef2e73165042d53fcc317a",
            "x-forwarded-for": "103.107.130.22",
            "x-forwarded-port": "443",
            "x-forwarded-proto": "https",
            "date": "Sun, 31 Jan 2021 00:21:45 GMT",
        },
        "requestContext": {
            "accountId": "143841941773",
            "apiId": "r03szwwq41",
            "domainName": "api.v2.sondehub.org",
            "domainPrefix": "api",
            "http": {
                "method": "PUT",
                "path": "/sondes/telemetry",
                "protocol": "HTTP/1.1",
                "sourceIp": "103.107.130.22",
                "userAgent": "autorx-1.4.1-beta4",
            },
            "requestId": "Z_NJvh0RoAMEJaw=",
            "routeKey": "PUT /sondes/telemetry",
            "stage": "$default",
            "time": "31/Jan/2021:00:10:25 +0000",
            "timeEpoch": 1612051825409,
        },
        "body": "H4sIAOzVHGEAA22ST2/bMAzF7/sUhs+xJsn64+RWFOh2G9AOO6woDCZmUgOylMmyu27Yd5+oFm0GzDc+//hoPvr+dz2HY3qCiL2HCetdVUcYxjAHP2APSwp9/FlvqndsxTiPwRMpmGay2WMCQ8hydgEGjP0BnJvHU2FuzOcvt/+8PYd5TC8O96pjgguzsUy2Wm74wyUIPqH3UCZ9VNUTrFhNwYdzcEiOaZywj3jAccWBKMmlaHjXiO4rFztldkoxaVWn+HfiB0hIPf9B7Y5zxstT0An8coRDWiJGwr/BOIODMvX5XBxu75QowWAcwRWlNSYv0xZ12V+Czd0nUo/xJWMhtLK5dpBypQyTgtstCSUWy6xUpss1uAJw2zIuuaWeFV2/ZrFpmRFKd6/SI9lyttVW6Cw9Yr6iP5HYtkyLVlLvDGnOEvXsIZG1ZLZ8F/5Y0B+ey7DME7DEOfWUFyVgtG5JnT1V20IsefUGTujJqL6a4Ffw1bULy3ATQxYzcnHr+m3N1/Xef4oypR/QJTp2k7dotRbqz8OHvxLcNOCgAgAA",
        "isBase64Encoded": True,
    }
    print(lambda_handler(payload, {}))
