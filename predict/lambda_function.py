import boto3
import botocore.credentials
from botocore.awsrequest import AWSRequest
from botocore.endpoint import URLLib3Session
from botocore.auth import SigV4Auth
import json
import os
from datetime import datetime, timedelta, timezone
import sys
import traceback
import http.client
import math
import logging
import gzip
from io import BytesIO
import base64

HOST = os.getenv("ES")


def predict(event, context):
    path = "predictions-*/_search"
    payload = {
        "aggs": {
            "2": {
                "terms": {
                    "field": "serial.keyword",
                    "order": {
                        "_key": "desc"
                    },
                    "size": 1000
                },
                "aggs": {
                    "1": {
                        "top_hits": {
                            "_source": True,
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
        "size": 0,
        "stored_fields": [
            "*"
        ],
        "script_fields": {},
        "docvalue_fields": [
            {
                "field": "datetime",
                "format": "date_time"
            }
        ],
        "_source": {
            "excludes": []
        },
        "query": {
            "bool": {
                "must": [],
                "filter": [
                    {
                        "range": {
                            "datetime": {
                                "gte": "now-6h",
                                "lte": "now",
                                "format": "strict_date_optional_time"
                            }
                        }
                    }
                ],
                "should": [

                ],
                "must_not": []
            }
        }
    }

    if "queryStringParameters" in event:
        if "vehicles" in event["queryStringParameters"] and event["queryStringParameters"]["vehicles"] != "RS_*;*chase" and event["queryStringParameters"]["vehicles"] != "":   
            for serial in event["queryStringParameters"]["vehicles"].split(","):
                payload["query"]["bool"]["should"].append(
                    {
                        "match_phrase": {
                            "serial.keyword": serial
                        }
                    }
                )
            # for single sonde allow longer predictions
            payload['query']['bool']['filter'].pop(0)
    logging.debug("Start ES Request")
    results = es_request(payload, path, "GET")
    logging.debug("Finished ES Request")
    output = []
    for sonde in results['aggregations']['2']['buckets']:
        data = sonde['1']['hits']['hits'][0]['_source']
        output.append({
            "vehicle": data["serial"],
            "time": data['datetime'],
            "latitude": data['position'][1],
            "longitude": data['position'][0],
            "altitude":  data['altitude'],
            "ascent_rate": data['ascent_rate'],
            "descent_rate": data['descent_rate'],
            "burst_altitude": data['burst_altitude'],
            "descending": 1 if data['descending'] == True else 0,
            "landed":  1 if data['landed'] == True else 0,
            "data":  json.dumps(data['data'])
        })

    compressed = BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode='w') as f:
        json_response = json.dumps(output)
        f.write(json_response.encode('utf-8'))
    
    gzippedResponse = compressed.getvalue()
    return {
            "body": base64.b64encode(gzippedResponse).decode(),
            "isBase64Encoded": True,
            "statusCode": 200,
            "headers": {
                "Content-Encoding": "gzip",
                "content-type": "application/json"
            }
            
        }

def es_request(payload, path, method):
    # get aws creds
    session = boto3.Session()

    params = json.dumps(payload)

    compressed = BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode='w') as f:
        f.write(params.encode('utf-8'))
    params = compressed.getvalue()

    headers = {"Host": HOST, "Content-Type": "application/json",
               "Content-Encoding": "gzip"}
    request = AWSRequest(
        method=method, url=f"https://{HOST}/{path}", data=params, headers=headers
    )
    SigV4Auth(boto3.Session().get_credentials(),
              "es", "us-east-1").add_auth(request)

    session = URLLib3Session()
    r = session.send(request.prepare())
    return json.loads(r.text)


if __name__ == "__main__":
    # print(get_sondes({"queryStringParameters":{"lat":"-28.22717","lon":"153.82996","distance":"50000"}}, {}))
    # mode: 6hours
    # type: positions
    # format: json
    # max_positions: 0
    # position_id: 0
    # vehicles: RS_*;*chase
    print(predict(
          {"queryStringParameters": {
              "vehicles": ""
          }}, {}
          ))


# get list of sondes,    serial, lat,lon, alt
   #           and        current rate
# for each one, request http://predict.cusf.co.uk/api/v1/?launch_latitude=-37.8136&launch_longitude=144.9631&launch_datetime=2021-02-22T00:15:18.513413Z&launch_altitude=30000&ascent_rate=5&burst_altitude=30000.1&descent_rate=5
   # have to set the burst alt slightly higher than the launch
