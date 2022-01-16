import json
import boto3
import zlib
import base64
import datetime
from email.utils import parsedate
import os


def set_connection_header(request, operation_name, **kwargs):
    request.headers['Connection'] = 'keep-alive'

sns = boto3.client("sns",region_name="us-east-1")
sns.meta.events.register('request-created.sns', set_connection_header)

def telemetry_filter(telemetry):
    if "dev" in telemetry:
        return (False, "All checks passed however payload contained dev flag so will not be uploaded to the database")

    return (True, "")


def post(payload):
    sns.publish(
                TopicArn=os.getenv("HAM_SNS_TOPIC"),
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

