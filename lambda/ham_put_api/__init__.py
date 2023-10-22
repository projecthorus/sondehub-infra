import json
import boto3
import zlib
import base64
import datetime
from email.utils import parsedate
import os
import config_handler

def set_connection_header(request, operation_name, **kwargs):
    request.headers['Connection'] = 'keep-alive'

sns = boto3.client("sns",region_name="us-east-1")
sns.meta.events.register('request-created.sns', set_connection_header)

TOPIC = config_handler.get("HAM_SNS","TOPIC")

def check_fields_are_number(field, telemetry):
    if type(telemetry[field]) != float and type(telemetry[field]) != int:
        return (False, f"{field} should not be a float")
    return (True, "")

def telemetry_filter(telemetry):
    fields_to_check = ["alt", "lat", "lon"]
    required_fields = ["datetime", "uploader_callsign", "software_name"] + fields_to_check
    for field in required_fields:
        if field not in telemetry:
            return (False, f"Missing {field} field")    
    for field in fields_to_check:
        field_check = check_fields_are_number(field, telemetry)
        if  field_check[0] == False:
            return field_check
    if "dev" in telemetry:
        return (False, "All checks passed however payload contained dev flag so will not be uploaded to the database")

    return (True, "")

# Returns true for anything that should be hidden
def telemetry_hide_filter(telemetry):
    # Default Horus Binary callsigns
    if telemetry["payload_callsign"] in ['4FSKTEST','4FSKTEST-V2']:
        return True

    # Default pysondehub uploader callsign
    if telemetry["uploader_callsign"] in ['MYCALL']:
        return True

    return False

def post(payload):
    sns.publish(
                TopicArn=TOPIC,
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

    payloads = json.loads(event["body"])
    to_sns = []
    errors = []
    warnings = []



    for payload in payloads:
        if "user-agent" in event["headers"]:
            event["time_server"] = datetime.datetime.now().isoformat()
            payload["user-agent"] = event["headers"]["user-agent"]
        payload["position"] = f'{payload["lat"]},{payload["lon"]}'

        payload["upload_time"] = datetime.datetime.now().isoformat()

        valid, error_message = telemetry_filter(payload)

        try:
            _delta_time = (
                datetime.datetime.now() - datetime.datetime.fromisoformat(payload["datetime"].replace("Z",""))
            ).total_seconds()
        except:
            errors.append({
                "error_message": "Unable to parse datetime",
                "payload": payload
            })

        future_time_threshold_seconds = 60
        time_threshold_hours = 24
        if _delta_time < -future_time_threshold_seconds:
            payload["telemetry_hidden"] = True
            warnings.append({
                "warning_message": f"Payload reported time too far in the future. Either sonde time or system time is invalid. (Threshold: {future_time_threshold_seconds} seconds)",
                "payload": payload
            })
        if "historical" not in payload or payload['historical'] == False:
            if abs(_delta_time) > (3600 * time_threshold_hours):
                payload["telemetry_hidden"] = True
                warnings.append({
                    "warning_message": f"Payload reported time too far from current UTC time. Either payload time or system time is invalid. (Threshold: {time_threshold_hours} hours)",
                    "payload": payload
                })

        if not valid:
            errors.append({
                "error_message": error_message,
                "payload": payload
            })
        else:
            # Apply hide field for anything that matches our filters
            if telemetry_hide_filter(payload):
                payload["telemetry_hidden"] = True
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


    post(to_sns)
    return errors, warnings
def lambda_handler(event, context):
    try:
        errors, warnings = upload(event, context)
    except zlib.error:
        return {"statusCode": 400, "body": "Could not decompress"}
    except json.decoder.JSONDecodeError:
        return {"statusCode": 400, "body": "Not valid json"}
    error_message = {
        "message": "some or all payloads could not be processed or have warnings",
        "errors": errors,
        "warnings": warnings
    }
    if errors or warnings:
        output = {
            "statusCode": 202, 
            "body": json.dumps(error_message),
            "headers": {
                "content-type": "application/json"
            }
        }
        print({
            "statusCode": 202, 
            "body": error_message,
            "headers": {
                "content-type": "application/json"
            }
        })
        return output
    else:
        return {"statusCode": 200, "body": "^v^ telm logged"}

