import json
from botocore.awsrequest import AWSRequest
from botocore.endpoint import URLLib3Session
from botocore.auth import SigV4Auth
import boto3
import botocore.credentials
import os
from io import BytesIO
import gzip
null = None
HOST = os.getenv("ES")

def es_request(payload, path, method):
    # get aws creds
    session = boto3.Session()
    compressed = BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode='w') as f:
        f.write(payload.encode('utf-8'))
    payload = compressed.getvalue()
    headers = {"Host": HOST, "Content-Type": "application/json", "Content-Encoding":"gzip"}
    request = AWSRequest(
        method="POST", url=f"https://{HOST}/{path}", data=payload, headers=headers
    )
    SigV4Auth(boto3.Session().get_credentials(), "es", "us-east-1").add_auth(request)

    session = URLLib3Session()
    r = session.send(request.prepare())
    if r.status_code != 200:
        raise RuntimeError
    return json.loads(r.text)


def lambda_handler(event, context):
    payloads = {}
    for record in event['Records']:
        sns_message = json.loads(record["body"])
        if type(json.loads(sns_message["Message"])) == dict:
            incoming_payloads = [json.loads(sns_message["Message"])]
        else:
            incoming_payloads = json.loads(sns_message["Message"])
        for payload in incoming_payloads:
            index = payload['datetime'][:7]
            
            if index not in payloads: # create index if not exists
                payloads[index] = []
                
            payloads[index].append(payload)
        
    for index in payloads:
        body=""
        for payload in payloads[index]:
            body += "{\"index\":{}}\n" + json.dumps(payload) + "\n"
        body += "\n"

        result = es_request(body, f"telm-{index}/_doc/_bulk", "POST")
        if 'errors' in result and result['errors'] == True:
            error_types = [x['index']['error']['type'] for x in result['items'] if 'error' in x['index']] # get all the error types
            error_types = [a for a in error_types if a != 'mapper_parsing_exception'] # filter out mapper failures since they will never succeed
            if error_types:
                print(event)
                print(result)
                raise RuntimeError