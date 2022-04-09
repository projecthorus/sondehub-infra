import json
import logging
import gzip
from io import BytesIO
import base64
import es




def predict(event, context):
    path = "ham-predictions-*/_search"
    payload = {
        "aggs": {
            "2": {
                "terms": {
                    "field": "payload_callsign.keyword",
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
            for payload_callsign in event["queryStringParameters"]["vehicles"].split(","):
                payload["query"]["bool"]["should"].append(
                    {
                        "match_phrase": {
                            "payload_callsign.keyword": payload_callsign
                        }
                    }
                )
            # for single sonde allow longer predictions
            payload['query']['bool']['filter'].pop(0)
    logging.debug("Start ES Request")
    results = es.request(json.dumps(payload), path, "GET")
    logging.debug("Finished ES Request")
    output = []
    for sonde in results['aggregations']['2']['buckets']:
        data = sonde['1']['hits']['hits'][0]['_source']
        output.append({
            "vehicle": data["payload_callsign"],
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
