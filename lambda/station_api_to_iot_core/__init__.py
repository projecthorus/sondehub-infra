import json
import zlib
import base64
import datetime
from email.utils import parsedate
import os
import base64
import gzip
from io import BytesIO
import boto3
import config_handler

CALLSIGN_BLOCK_LIST = ["CHANGEME_RDZTTGO", "14FRS119_LE JUDA", "CHANGEME"]

import es


# Setup SNS

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
                TopicArn=config_handler.get("SNS","TOPIC"),
                Message=payload
    )

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
                - datetime.datetime.fromtimestamp(event["requestContext"]["timeEpoch"]/1000, datetime.UTC)
            ).total_seconds()
        except:
            pass
    try:
        payload = json.loads(event["body"])
    except:
        return {"statusCode": 400, "body": "JSON decode issue"}
    print(json.dumps(event))
    if "user-agent" in event["headers"]:
        event["time_server"] = datetime.datetime.now(datetime.UTC).isoformat()
        payload["user-agent"] = event["headers"]["user-agent"]
    if time_delta:
        payload["upload_time_delta"] = time_delta

    payload.pop("uploader_contact_email", None)


    # Software allow-list - run this before doing any of the other checks.
    # This needs to be synced with the list in sonde_api_to_iot_core, so should probably live elsewhere.
    allowed_sonde_software = [
        "radiosonde_auto_rx",       # https://github.com/projecthorus/radiosonde_auto_rx/wiki
        "rdzTTGOsonde",             # https://github.com/dl9rdz/rdz_ttgo_sonde
        "dxlAPRS-SHUE",             # https://github.com/Eshco93/dxlAPRS-SHUE
        "SondeMonitor",             # https://www.coaa.co.uk/sondemonitor.htm
        "RS41Tracker",              # https://escursioni.altervista.org/Radiosonde/
        "SDRangel",                 # https://www.sdrangel.org/
        "OpenWebRX",                # https://github.com/luarvique/openwebrx
        "DsRS41Tracker",            # https://github.com/novarobot/DsRS41Tracker
        "OpenWXSDR",                # https://github.com/DL2MF/OpenWXSDR
        "SondeFox",                 # (no link)
        "rtlsdr_multisonde_go",     # (no link)
        "gsnext-rdz"                # (no link)
    ]

    if payload["software_name"] not in allowed_sonde_software:
        if 'mobile' in payload and payload['mobile']:
            # Pass through mobile station data (chase cars)
            pass
        else:
            return {"statusCode": 403, "body": "This software is unknown to us! Please ask the software developer to refer to https://github.com/projecthorus/sondehub-infra/wiki/Sonde-Telemetry-Validation, then contact us at support@sondehub.org or on sondehub.org/go/discord for data validation."}

    # Bad SDRangel version uploading lister positions too often.
    if (
        "software_name" in payload and 
        payload["software_name"] == "SDRangel" and 
        "software_version" in payload and 
        payload["software_version"] == "7.22.5"
        ):
        return {"statusCode": 403, "body": "This version is blocked"}


    # clean up None reports
    if "uploader_position" in payload and None == payload["uploader_position"] or None in payload["uploader_position"]:
        payload.pop("uploader_position", None)


    if "uploader_position" in payload:
        (payload["uploader_alt"], payload["uploader_position_elk"]) = (
                payload["uploader_position"][2],
                f"{payload['uploader_position'][0]},{payload['uploader_position'][1]}",
            )

    if payload["uploader_callsign"] in CALLSIGN_BLOCK_LIST:
        return  {"statusCode": 403, "body": "callsign blocked or invalid - please use a unique callsign!"}
    
    index = datetime.datetime.now(datetime.UTC).strftime("listeners-%Y-%m")
    payload["ts"] = datetime.datetime.now(datetime.UTC).isoformat()

    post([payload])
    es.request(json.dumps(payload),f"{index}/_doc","POST")

    return {"statusCode": 200, "body": "^v^ telm logged"}