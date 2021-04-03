import boto3
import botocore.credentials
from botocore.awsrequest import AWSRequest
from botocore.endpoint import URLLib3Session
from botocore.auth import SigV4Auth
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all
import json
import os
from datetime import datetime, timedelta, timezone
import sys, traceback

HOST = os.getenv("ES")
# get current sondes, filter by date, location

def history(event, context):
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
        data["1"]["hits"]["hits"][0]["_source"] 
        for data in results["aggregations"]["3"]["buckets"] 
    ]
    return json.dumps(output)



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
            {"pathParameters": {"serial": "S4720140"}}, {}
        )
    )




