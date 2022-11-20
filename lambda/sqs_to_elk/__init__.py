import json
import es
import zlib
import base64
import datetime

def lambda_handler(event, context):
    payloads = []
    for record in event['Records']:
        sns_message = json.loads(record["body"])
        try:
            decoded = json.loads(zlib.decompress(base64.b64decode(sns_message["Message"]), 16 + zlib.MAX_WBITS))
        except:
            decoded = json.loads(sns_message["Message"])
        if type(decoded) == dict:
            incoming_payloads = [decoded]
        else:
            incoming_payloads = decoded
        year, week = datetime.datetime.now().isocalendar()[:2]
        index = f"{year}-{week}"
        payloads += incoming_payloads

    body=""
    for payload in payloads:
        body += "{\"index\":{}}\n" + json.dumps(payload) + "\n"
    body += "\n"

    result = es.request(body, f"telm-{index}/_bulk", "POST")
    if 'errors' in result and result['errors'] == True:
        error_types = [x['index']['error']['type'] for x in result['items'] if 'error' in x['index']] # get all the error types
        print(event)
        print(result)
        error_types = [a for a in error_types if a != 'mapper_parsing_exception'] # filter out mapper failures since they will never succeed
        if error_types:
            raise RuntimeError