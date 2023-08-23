import json
import boto3
import zlib
import base64
import datetime
from email.utils import parsedate
import os
import re
from math import radians, degrees, sin, cos, atan2, sqrt, pi
import statistics
from collections import defaultdict
import time
import traceback
import sys

import base64
import gzip
from io import BytesIO

logs = boto3.client('logs')
sequenceToken = None

def handle_error(message, event, stream_name):
    global sequenceToken
    print(message)
    if sequenceToken:
        response = logs.put_log_events(
            logGroupName='/ingestion',
            logStreamName=stream_name,
            logEvents=[
                {
                    'timestamp': time.time_ns() // 1_000_000,
                    'message': json.dumps(event)
                },
                {
                    'timestamp': time.time_ns() // 1_000_000,
                    'message': message
                },
            ],
            sequenceToken=sequenceToken
        )
        sequenceToken = response['nextSequenceToken']
    else:
        try:
            log_stream = logs.create_log_stream(
            logGroupName='/ingestion',
            logStreamName=stream_name
        )
        except: # ignore times we fail to create a log_stream - its probably already created
            pass
        response = logs.put_log_events(
            logGroupName='/ingestion',
            logStreamName=stream_name,
            logEvents=[
                {
                    'timestamp': time.time_ns() // 1_000_000,
                    'message': json.dumps(event)
                },
                {
                    'timestamp': time.time_ns() // 1_000_000,
                    'message': message
                },
            ]
        )
        sequenceToken = response['nextSequenceToken']
    print(sequenceToken)

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
    return outliers

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

    if "subtype" in telemetry and telemetry["subtype"] == "DL0UJ-12":
        return (False,f"sondehub.org is not for use with amateur balloons. Use amateur.sondehub.org instead.")

    if "humidity" in telemetry and telemetry["humidity"] < 0:
        return (False,f"Humidity {telemetry['humidity']} is below 0")

    if "pressure" in telemetry and telemetry["pressure"] < 0:
        return (False,f"Pressure {telemetry['pressure']} is below 0")

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

    if "heading" in telemetry and telemetry["heading"] > 360:
            return (False,f"Heading {telemetry['heading']} is above 360")

    # DateTime Check
    
    try:
        _delta_time = (
            datetime.datetime.now() - datetime.datetime.fromisoformat(telemetry["datetime"].replace("Z",""))
        ).total_seconds()
    except:
        return (False, f"Unable to parse time")

    sonde_time_threshold = 48
    future_time_threshold_seconds = 60
    if _delta_time < -future_time_threshold_seconds:
        return (False, f"Sonde reported time too far in the future. Either sonde time or system time is invalid. (Threshold: {future_time_threshold_seconds} seconds)")
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
    if ("RS41" in telemetry["type"]) or ("RS92" in telemetry["type"]):
        vaisala_callsign_valid = re.match(r"^[C-Z]\d{7}$", _serial)
    else:
        vaisala_callsign_valid = False

    # Just make sure we're not getting the 'xxxxxxxx' unknown serial from the DFM decoder.
    if "DFM" in telemetry["type"]:
        dfm_callsign_valid = "x" not in _serial
    else:
        dfm_callsign_valid = False

    # Check Meisei sonde callsigns for validity.
    # meisei_ims returns a callsign of IMS100-xxxxxx until it receives the serial number, so we filter based on the x's being present or not.
    if "IMS100" in telemetry["type"] or "RS11G" in telemetry["type"] or "iMS-100" in telemetry["type"] or "RS-11G" in telemetry["type"]:
        meisei_callsign_valid = "x" not in _serial
    else:
        meisei_callsign_valid = False

    if "MRZ" in telemetry["type"]:
        mrz_callsign_valid = "x" not in _serial
    else:
        mrz_callsign_valid = False

    # If Vaisala or DFMs, check the callsigns are valid. If M10, iMet or LMS6, just pass it through - we get callsigns immediately and reliably from these.
    if not (
        vaisala_callsign_valid
        or dfm_callsign_valid
        or meisei_callsign_valid
        or mrz_callsign_valid
        or ("M10" in telemetry["type"])
        or ("M20" in telemetry["type"])
        or ("LMS" in telemetry["type"])
        or ("iMet" in telemetry["type"])
        or ("MTS01" in telemetry["type"])
    ):
        _id_msg = "Payload ID %s from Sonde type %s is invalid." % (telemetry["serial"], telemetry["type"])
        # Add in a note about DFM sondes and their oddness...
        if "DFM" in telemetry["serial"]:
            _id_msg += " Note: DFM sondes may take a while to get an ID."

        if "MRZ" in telemetry["serial"]:
            _id_msg += " Note: MRZ sondes may take a while to get an ID."

        return (False, _id_msg)
    # https://github.com/projecthorus/sondehub-infra/issues/56
    if "iMet-4" ==  telemetry["type"] or "iMet-1" ==  telemetry["type"]:
        if telemetry["software_name"] == "radiosonde_auto_rx":
            if parse_autorx_version(telemetry["software_version"]) < (1,5,9): 
                return (False,f"Autorx version is out of date and doesn't handle iMet-1 and iMet-4 radiosondes correctly. Please update to 1.5.9 or later")
    if "DFM" in telemetry["type"]:
        if telemetry["software_name"] == "SondeMonitor":
            if parse_sondemonitor_version(telemetry["software_version"]) < (6,2,8,7): 
                return (False,f"SondeMonitor version is out of date and doesn't handle DFM radiosondes correctly. Please update to 6.2.8.7 or later")

    # block callsigns
    if telemetry["uploader_callsign"] in ["M00ON-5", "LEKUKU", "BS144", "Carlo-12", "GAB1", "FEJ-5", "KR001"]:
        return (False, "Something is wrong with the data your station is uploading, please contact us so we can resolve what is going on. support@sondehub.org")

    if "dev" in telemetry:
        return (False, "All checks passed however payload contained dev flag so will not be uploaded to the database")

    return (True, "")

def parse_sondemonitor_version(version):
    try:
        m = re.search(r'(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?', version)
        return tuple([int(x if x != None else 0) for x in m.groups()])
    except:
        return (0,0,0,0)

def parse_autorx_version(version):
    try:
        m = re.search(r'(\d+)\.(\d+)(?:\.(\d+))?', version)
        return tuple([int(x if x != None else 0) for x in m.groups()])
    except:
        return (0,0,0)

def set_connection_header(request, operation_name, **kwargs):
    request.headers['Connection'] = 'keep-alive'

sns = boto3.client("sns",region_name="us-east-1")
sns.meta.events.register('request-created.sns', set_connection_header)

def post(payload):
    compressed = BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode='w') as f:
        f.write(json.dumps(payload).encode('utf-8'))
    payload = base64.b64encode(compressed.getvalue()).decode("utf-8")
    sns.publish(
                TopicArn=os.getenv("SNS_TOPIC"),
                Message=payload
    )

def upload(event, context, orig_event):
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
                - datetime.datetime.utcfromtimestamp(event["requestContext"]["timeEpoch"]/1000)
            ).total_seconds()
        except:
            pass
    # check if event is an array
    payloads = json.loads(event["body"])
    if type(payloads) != list:
        raise TypeError("Expecting list of payloads")
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
                pass
                #handle_error(f"Outlier check detected outlier, serial: {check_data[0]['serial']}", orig_event, context.log_stream_name)
            for index in lat_outliers:
                payload_serials[serial][index]["lat_outlier"] = True
            for index in lon_outliers:
                payload_serials[serial][index]["lon_outliers"] = True
            for index in alt_outliers:
                payload_serials[serial][index]["alt_outliers"] = True
        elif "DFM" in check_data[0]["type"]: # if the sonde is a DFM and there's not enough payloads to perform z check then bail out
            fail_dfm = False
            for data in check_data:
                if data['alt'] > 2500:
                    fail_dfm = True
            if fail_dfm == True:
                [x.update(dfm_failure=True) for x in payload_serials[serial]]



        #generate error messages and regenerate payload list of bad data removed
        for payload in payload_serials[serial]:
            if "alt_outliers" in payload or "lon_outliers" in payload or "lat_outlier" in payload:
                errors.append({
                    "error_message": f"z-check failed - payload GPS may not be valid for {payload['serial']}.",
                    "payload": payload
                })
            elif "dfm_failure" in payload:
                errors.append({
                    "error_message": f"DFM radiosonde above 1000 and not enough data to perform z-check. Not adding DB to protect against double frequency usage.",
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
                elif payload['uploader_position'][0] == None or payload['uploader_position'][1] == None:
                    payload.pop("uploader_position")
                else:
                    (payload["uploader_alt"], payload["uploader_position"]) = (
                        payload["uploader_position"][2],
                        f"{payload['uploader_position'][0]},{payload['uploader_position'][1]}",
                    )

            to_sns.append(payload)

    # if to_sns:
    #     last = to_sns.pop()
    #     to_sns = to_sns[::3]
    #     to_sns.append(last)
    if len(to_sns) > 0:
        post(to_sns)
    return errors
def lambda_handler(event, context):
    orig_event = event.copy()
    try:
        try:
            errors = upload(event, context, orig_event)
        except zlib.error:
            response = {"statusCode": 400, "body": "Could not decompress"}
            handle_error(json.dumps(response), orig_event, context.log_stream_name)
            return response
        except json.decoder.JSONDecodeError:
            response = {"statusCode": 400, "body": "Not valid json"}
            handle_error(json.dumps(response), orig_event, context.log_stream_name)
            return response
        except TypeError as e:
            response = {"statusCode": 400, "body": str(e)}
            handle_error(json.dumps(response), orig_event, context.log_stream_name)
            return response            
        error_message = {
            "message": "some or all payloads could not be processed",
            "errors": errors
        }
        if errors:
            output = {
                "statusCode": 202, 
                "body": json.dumps(error_message),
                "headers": {
                    "content-type": "application/json"
                }
            }
            #handle_error(json.dumps(output), orig_event, context.log_stream_name)
            return output
        else:
            return {"statusCode": 200, "body": "^v^ telm logged"}
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        handle_error("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)), orig_event, context.log_stream_name)
        return {"statusCode": 400, "body": "Error processing request. Check payloads format."}

