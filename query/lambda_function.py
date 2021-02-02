import boto3
import botocore.credentials
from botocore.awsrequest import AWSRequest
from botocore.endpoint import URLLib3Session
from botocore.auth import SigV4Auth
import json
import os

HOST=os.getenv("ES")
# get current sondes, filter by date, location

def get_sondes(event, context):
    path = "telm-*/_search"
    payload = {
        "aggs": {
            "2": {
            "terms": {
                "field": "serial.keyword",
                "order": {
                "_key": "desc"
                },
                "size": 10000
            },
            "aggs": {
                "1": {
                "top_hits": {
                    "size": 1,
                    "sort": [
                    {
                        "datetime": {
                        "order": "desc"
                        }
                    }
                    ]
                }
                }
            }
            }
        },
        "query": {
            "bool": {
            "filter": [
                {
                    "match_all": {}
                }
            ]
            }
        }
    }

    # add filters
    if "queryStringParameters" in event:
        if "last" in event["queryStringParameters"]:
            payload["query"]["bool"]["filter"].append(
                {
                    "range": {
                        "datetime": {
                            "gte": f"now-{int(event['queryStringParameters']['last'])}s",
                            "lte": "now"
                        }
                    }
                }
            )
        if "lat" in event["queryStringParameters"] and "lon" in event["queryStringParameters"] and "distance" in event["queryStringParameters"]:
            payload["query"]["bool"]["filter"].append(
                {
                    "geo_distance": {
                        "distance": f"{int(event['queryStringParameters']['distance'])}m",
                        "position": {
                            "lat": float(event['queryStringParameters']['lat']),
                            "lon": float(event['queryStringParameters']['lon'])
                        }
                    }
                }
            )
    # if the user doesn't specify a range we should add one - 24 hours is probably a good start
    if "range" not in payload["query"]["bool"]["filter"]:
        payload["query"]["bool"]["filter"].append(
                {
                    "range": {
                        "datetime": {
                            "gte": "now-1d",
                            "lte": "now"
                        }
                    }
                }
            )
            
    results = es_request(payload, path, "POST")
    buckets = results["aggregations"]["2"]["buckets"]
    sondes = {  bucket["1"]["hits"]["hits"][0]["_source"]["serial"]: bucket["1"]["hits"]["hits"][0]["_source"]  for bucket in buckets}
    return json.dumps(sondes)

def es_request(payload, path, method):
    #get aws creds
    session = boto3.Session()

    params = json.dumps(payload)
    headers = {
    'Host': HOST,
    'Content-Type': "application/json"
    }
    request = AWSRequest(method="POST", url=f"https://{HOST}/{path}", data=params, headers=headers)
    SigV4Auth(boto3.Session().get_credentials(), "es", "us-east-1").add_auth(request)    


    session = URLLib3Session()
    r = session.send(request.prepare())
    return json.loads(r.text)



if __name__ == "__main__":
    #print(get_sondes({"queryStringParameters":{"lat":"-28.22717","lon":"153.82996","distance":"50000"}}, {}))
    print(get_sondes({},{}))