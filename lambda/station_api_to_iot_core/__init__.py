import json
import zlib
import base64
import datetime
from email.utils import parsedate

CALLSIGN_BLOCK_LIST = ["CHANGEME_RDZTTGO"]

import es

def lambda_handler(event, context):
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
    try:
        payload = json.loads(event["body"])
    except:
        return {"statusCode": 400, "body": "JSON decode issue"}
    print(payload)
    if "user-agent" in event["headers"]:
        event["time_server"] = datetime.datetime.now().isoformat()
        payload["user-agent"] = event["headers"]["user-agent"]
    if time_delta:
        payload["upload_time_delta"] = time_delta

    payload.pop("uploader_contact_email", None)

    # clean up None reports

    if "uploader_position" in payload and None == payload["uploader_position"] or None in payload["uploader_position"]:
        payload.pop("uploader_position", None)
    
    if "uploader_position" in payload:
        (payload["uploader_alt"], payload["uploader_position_elk"]) = (
                payload["uploader_position"][2],
                f"{payload['uploader_position'][0]},{payload['uploader_position'][1]}",
            )
    if payload["uploader_callsign"] in CALLSIGN_BLOCK_LIST:
        return  {"statusCode": 403, "body": "callsign blocked or invalid"}
    index = datetime.datetime.utcnow().strftime("listeners-%Y-%m")
    payload["ts"] = datetime.datetime.utcnow().isoformat()

    es.request(json.dumps(payload),f"{index}/_doc","POST")

    return {"statusCode": 200, "body": "^v^ telm logged"}