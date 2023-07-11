import json
import zlib
import base64
import datetime
from email.utils import parsedate

import es

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
    payload["datetime"] = datetime.datetime.utcnow().isoformat()
    if type(payload['ascent_rate']) not in [float, int]:
        return {"statusCode": 400, "body": "ascent_rate must be a number"}
    if type(payload['descent_rate']) not in [float, int]:
        return {"statusCode": 400, "body": "descent_rate must be a number"}
    if type(payload['peak_altitude']) not in [float, int]:
        return {"statusCode": 400, "body": "peak_altitude must be a number"}
    if type(payload['float_expected']) not in [bool]:
        return {"statusCode": 400, "body": "float_expected must be a bool"}
    payload['identity'] = event['requestContext']['authorizer']['iam']['cognitoIdentity']['amr'][2]

    es.request(json.dumps(payload),f"flight-doc/_doc","POST")

    return {"statusCode": 200, "body": "^v^ updated"}

def query(event, context):
    payload_callsign = event['pathParameters']['payload_callsign']
    payload = {
        "sort": [
            { "datetime" : {"order" : "desc"}}
        ],
        "size": 1,
        "query": {
            "bool": {
            "filter": [
                {
                    "term": {
                        "payload_callsign.keyword": payload_callsign
                    }
                }
            ]
            }
        }
    }
    results = es.request(json.dumps(payload),f"flight-doc/_search","POST")
    if len(results['hits']['hits']) > 0 :
        return {"statusCode": 200, "body": json.dumps(results['hits']['hits'][0]['_source'])}
    else:
        return {"statusCode": 404, "body": "not found"}