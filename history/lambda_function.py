import boto3
import botocore.credentials
from botocore.awsrequest import AWSRequest
from botocore.endpoint import URLLib3Session
from botocore.auth import SigV4Auth
import json
import os
from datetime import datetime, timedelta, timezone
import sys, traceback
import uuid


# TODO , HEAD S3 object, if it's less than 24 hours check ES, else 302 to bucket

HOST = os.getenv("ES")
# get current sondes, filter by date, location

def history(event, context):
    s3 = boto3.resource('s3')
    serial = str(event["pathParameters"]["serial"])

    # if there's a historic file created for this sonde, use that instead
    try:
        object = s3.Object('sondehub-history', f'serial/{serial}.json.gz')
        object.load()
        return {"statusCode": 302, "headers": {"Location": f'https://{object.bucket_name}.s3.amazonaws.com/{object.key}'}}
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            pass
        else:
            # Something else has gone wrong.
            raise
    path = "telm-*/_search"
    payload = {
        "aggs": {
            "3": {
                "date_histogram": {
                    "field": "datetime",
                    "fixed_interval": "1s",
                    "min_doc_count": 1,
                },
                "aggs": {
                    "1": {
                        "top_hits": {
                            "size": 1,
                            "sort": [{"datetime": {"order": "desc"}}],
                        }
                    }
                },
            }
        },
        "query": {
            "bool": {
                "filter": [
                    {"match_all": {}},
                    {
                        "match_phrase": {
                        "serial": str(event["pathParameters"]["serial"])
                        }
                    }
                ]
            }
        },
    }
    
    results = es_request(payload, path, "POST")
    output = [
        {k: v for k, v in data["1"]["hits"]["hits"][0]["_source"].items() if k != 'user-agent' and k != 'upload_time_delta'}
        
        for data in results["aggregations"]["3"]["buckets"] 
    ]
    s3 = boto3.resource('s3')
    object = s3.Object('sondehub-open-data', 'export/' + str(uuid.uuid4()))
    object.put(Body=json.dumps(output).encode('utf-8'), ACL='public-read', ContentType='application/json')
    return {"statusCode": 302, "headers": {"Location": f'https://{object.bucket_name}.s3.amazonaws.com/{object.key}'}}



def es_request(payload, path, method):
    # get aws creds
    session = boto3.Session()

    params = json.dumps(payload)
    headers = {"Host": HOST, "Content-Type": "application/json"}
    request = AWSRequest(
        method="POST", url=f"https://{HOST}/{path}", data=params, headers=headers
    )
    SigV4Auth(boto3.Session().get_credentials(), "es", "us-east-1").add_auth(request)

    session = URLLib3Session()
    r = session.send(request.prepare())
    return json.loads(r.text)


if __name__ == "__main__":
    print(
        history(
            {"pathParameters": {"serial": "N4750769"}}, {}
        )
    )




