import json
import boto3
import botocore.credentials
from botocore.awsrequest import AWSRequest
from botocore.endpoint import URLLib3Session
from botocore.auth import SigV4Auth

import zlib
import base64
import datetime
import os

HOST = os.getenv("ES")

sqs = boto3.client('sqs', region_name="us-east-1")

def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]

def es_request(payload, path, method):
    session = boto3.Session()

    params = json.dumps(payload)
    headers = {"Host": HOST, "Content-Type": "application/json"}
    request = AWSRequest(
        method=method, url=f"https://{HOST}/{path}", data=params, headers=headers
    )
    SigV4Auth(boto3.Session().get_credentials(),
              "es", "us-east-1").add_auth(request)

    session = URLLib3Session()
    r = session.send(request.prepare())
    return json.loads(r.text)


def handler(event, context):
    query = {
        "aggs": {
            "serials": {
                "terms": {
                    "field": "serial.keyword",
                    "size": 10000
                }
            }
        },
        "size": 0,
        "_source": {
            "excludes": []
        },
        "query": {
            "bool": {
                "must_not": [{"match_phrase": {"serial": "xxxxxxxx"}}],
                "filter": [
                    {
                        "range": {
                            "datetime": {
                                "gte": "now-24h",
                                "format": "strict_date_optional_time"
                            }
                        }
                    }
                ]
            }
        }
    }

    results = es_request(query, "telm-*/_search", "POST")
    serials = [ x['key'] for x in results['aggregations']['serials']['buckets'] ]
    for serial_batch in batch(serials, 10):
        sqs.send_message_batch(
            QueueUrl="https://sqs.us-east-1.amazonaws.com/143841941773/update-history",
            Entries=[
                {
                    "Id": str(serial_batch.index(x)),
                    "MessageBody": x
                }
            for x in serial_batch]
        )
    return [ x['key'] for x in results['aggregations']['serials']['buckets'] ]
    #TODO add to SQS queue

if __name__ == "__main__":
    print(handler({}, {}))

# this script will find list of sondes seen in the last 48 hours and add them to the queue to be updated (including the first and last date they were seen)
