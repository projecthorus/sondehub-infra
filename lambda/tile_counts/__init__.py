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


def lambda_handler(event, context):
    if "isBase64Encoded" in event and event["isBase64Encoded"] == True:
        event["body"] = base64.b64decode(event["body"])
    if (
        "content-encoding" in event["headers"]
        and event["headers"]["content-encoding"] == "gzip"
    ):
        event["body"] = zlib.decompress(event["body"], 16 + zlib.MAX_WBITS)
    try:
        payload = json.loads(event["body"])
    except:
        return {"statusCode": 400, "body": "JSON decode issue"}
    print(json.dumps(payload))
    