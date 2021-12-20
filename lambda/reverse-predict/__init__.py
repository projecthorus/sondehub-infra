import json
from datetime import datetime, timedelta, timezone
import logging
import gzip
from io import BytesIO
import base64
import es

def predict(event, context):
    path = "reverse-prediction-*/_search"


    durations = {  # ideally we shouldn't need to predefine these, but it's a shit load of data and we don't need want to overload ES
        "3d": (259200, 1200),  # 3d, 20m
        "1d": (86400, 600),  # 1d, 10m
        "12h": (43200, 600),  # 1d, 10m
        "6h": (21600, 120),  # 6h, 1m
        "3h": (10800, 60),  # 3h, 10s
        "1h": (3600, 40),
        "30m": (1800, 20),
        "1m": (60, 1),
        "15s": (15, 1),
        "0": (0, 1) # for getting a single time point
    }
    duration_query = "6h"

    if (
        "queryStringParameters" in event
        and "duration" in event["queryStringParameters"]
    ):
        if event["queryStringParameters"]["duration"] in durations:
            duration_query = event["queryStringParameters"]["duration"]
        else:
            return f"Duration must be either {', '.join(durations.keys())}"

    if (
        "queryStringParameters" in event
        and "datetime" in event["queryStringParameters"]
    ):
        requested_time = datetime.fromisoformat(
            event["queryStringParameters"]["datetime"].replace("Z", "+00:00")
        )
    else:
        requested_time = datetime.now(timezone.utc)

    (duration, interval) = durations[duration_query]

    lt = requested_time + timedelta(0, 1)
    gte = requested_time - timedelta(0, duration)
    

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
                            "datetime": {"gte": gte.isoformat(), "lt": lt.isoformat()}
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
    results = es.request(json.dumps(payload), path, "GET")
    logging.debug("Finished ES Request")
    output = {x['1']['hits']['hits'][0]['_source']['serial']: x['1']['hits']['hits'][0]['_source'] for x in results['aggregations']['2']['buckets']}

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

