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
import statistics
from collections import defaultdict

def z_check(data, threshold):
    outliers = []
    mean = statistics.mean(data)
    sd = statistics.stdev(data)
    for index, i in enumerate(data): 
        try:
            z = (i-mean)/sd # calculate z-score
        except ZeroDivisionError:
            continue
        if abs(z) > threshold:  # identify outliers
            outliers.append(index) # add to the empty list
        # print outliers    
    if outliers:
        print("The detected outliers are: ", outliers)
        print("Data : ", data)
    return outliers

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

    if telemetry["alt"] == 0:
        return (False,f"Sonde {telemetry['serial']} altitude is exactly 0m. Position is likely incorrect")


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

    # perform z check
    payload_serials = defaultdict(list)
    for payload in payloads:
        payload_serials[payload['serial']].append(payload)
    # rebuild payloads with the outliers marked
    payloads = []
    for serial in payload_serials:
        check_data = payload_serials[serial]
        if len(check_data) > 10: # need at least 10 payloads to be useful
            lats = [ x['lat'] for x in check_data ]
            lons = [ abs(x['lon']) for x in check_data ]
            alts = [ x['alt'] for x in check_data ]
            lat_outliers = z_check(lats, 3)
            lon_outliers = z_check(lons, 3)
            alt_outliers = z_check(alts, 3)
            if lat_outliers or lon_outliers or alt_outliers:
                print("Outlier check detected outlier, serial:", check_data[0]["serial"])
            for index in lat_outliers:
                payload_serials[serial][index]["lat_outlier"] = True
            for index in lon_outliers:
                payload_serials[serial][index]["lon_outliers"] = True
            for index in alt_outliers:
                payload_serials[serial][index]["alt_outliers"] = True
        

        #generate error messages and regenerate payload list of bad data removed
        for payload in payload_serials[serial]:
            if "alt_outliers" in payload or "lon_outliers" in payload or "lat_outlier" in payload:
                errors.append({
                    "error_message": f"z-check failed - payload GPS may not be valid for {payload['serial']}.",
                    "payload": payload
                })
            else:
                payloads.append(payload)

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
    try:
        errors = upload(event, context)
    except zlib.error:
        return {"statusCode": 400, "body": "Could not decompress"}
    except json.decoder.JSONDecodeError:
        return {"statusCode": 400, "body": "Not valid json"}
    error_message = {
        "message": "some or all payloads could not be processed",
        "errors": errors
    }
    if errors:
        print(json.dumps({"statusCode": 202, "body": error_message}))
        return {"statusCode": 202, "body": error_message}
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
        "body": "H4sIACfzHmEAA+XaT2/bNhQA8Ps+hZGzw/HxP30utqHoLsNOGwaDjZnWgC15suysGPbdR6kiHZNUTKAGBFQBcghNKXriL+R7ZP78YbH4130vFg/H+rl9MY1dV2ZvH1aLh8ZstvWxrjZ2bU5tvW7+eVhGXc+2OW7rqusNiCPuO5wOu9psbLN+Mrvdcfup7/HuA7z/5bdH6HpF3UzV2qoy/X1+ZIsXc7aLfV3Vh3pn/T3b7d6uG/tkt2e76XoSTOARq0fQv2Ox4njFGeJcKyH/8NdsTGu76/LdKcL9V+i+N9Xp2Ty1p8Y23SU/N+Yl/Povh/427376NbyG08dXrViHdttsza4PRmGFKcP+k+fm67sFCpRqwJwOH+xM65qZRIqCZL6xf7OAkdJUwdBodl1PEEohRvyz2f3BNUokhoaz3a3ProUgYK+aPrsmN0pqaPps3QhXn1yjch39zY6mPbomPfz40bRtfxllIQj798lWT1+6J8YEcez7HqumDy48x6E+btsBSAjOB5Rg+RoaZ9y1/7f8rmRyxAQVuFQmm14my8nk1zJJP5A6kqkx0uy2TJqRKROZUiJK7ybT/dZxmdzL1HOSKZ1MzUAUyhTTyxQ5mepaZjeQDMtYpkAskckTmSyViVOZChCou8mkCMZlqqUPaDYyYYWpe0tESF4i03Unk8sUJCNTyYxMHsmUbmZi4rZMriOZDBGayJS4QCYplUlGXbrQfDhzcumewI21UoUup1/LRW4t1xmWIfMMLCXSNGbJUpYQsVQXgFcTZuj47SzpG0u5Xvp45uTSLW4uvdZFOWbPeHKXPOcSMjAVjWASjCjchgkxTI5IClO47FzfDSYgOQ4Tlj6gOcnsSlXFRelKLqeXKXMyeSqTxy45EgUuuYhcqkvS+WrCxAjfrMrL1/HwHBmXQ+2TQvmOVWrEKRUKClWq6VWqnMpMfnkZ++BSXsyNunSDQiKXHKUsBSDC78jyjelySDA5nk9JDiu3gnCGaWmC6d7Q1DAlTmGSDEsST5cUUJhC32Cp47JHIJ3JL+XF7z22ikYLcrL04cxJZbcvwqQkhSphepWQUYkz6SWncd1D2WXXMbikkUuCKE9cZjaKpKN0M728i0s8pJcuoDnJZIgJXFz4wPTHPjJz7EOwyMgME1qQqZBSBTJpIlNkZLpySN5N5mg93oXmw5mTS1eQS5CCFbqcviCXmYKc4MxOEQ+pqHfJKFLJcWTqEuIE0xU+kLjk+pIWfLtLHDZSMzKHrSIX0JxkuqGRTDJcKHP6Qx+ZOfQhkMsxZSJTZLaKUpk8njElCjPy1Vqu7nkcOVr7dMH5gOYk080HUmNauFUE028VyWirSPWDRzMyVXzow7T7M7wtU8fHkeKSAlz9C4e8n8zxtdx95MN52+Vf/wNvRwsqXCQAAA==",
        "isBase64Encoded": True,
    }
    print(lambda_handler(payload, {}))
