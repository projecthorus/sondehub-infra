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
from io import BytesIO
import gzip

HOST = os.getenv("ES")
http_session = URLLib3Session()

from multiprocessing import Process

def mirror(path,params):
    session = boto3.Session()
    headers = {"Host": "search-sondes-v2-hiwdpmnjbuckpbwfhhx65mweee.us-east-1.es.amazonaws.com", "Content-Type": "application/json", "Content-Encoding":"gzip"}
    request = AWSRequest(
        method="POST", url=f"https://search-sondes-v2-hiwdpmnjbuckpbwfhhx65mweee.us-east-1.es.amazonaws.com/{path}", data=params, headers=headers
    )
    SigV4Auth(boto3.Session().get_credentials(), "es", "us-east-1").add_auth(request)
    session = URLLib3Session()
    r = session.send(request.prepare())

def es_request(payload, path, method):
    # get aws creds
    session = boto3.Session()

    params = json.dumps(payload)
    compressed = BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode='w') as f:
        f.write(params.encode('utf-8'))
    params = compressed.getvalue()

    headers = {"Host": HOST, "Content-Type": "application/json", "Content-Encoding":"gzip"}

    request = AWSRequest(
        method="POST", url=f"https://{HOST}/{path}", data=params, headers=headers
    )
    SigV4Auth(boto3.Session().get_credentials(),
              "es", "us-east-1").add_auth(request)
    p = Process(target=mirror, args=(path,params)).start()
    r = http_session.send(request.prepare())
    return json.loads(r.text)


def getSonde(serial):
    query = {
        "aggs": {
            "1": {
                "top_hits": {
                    "docvalue_fields": [
                        {
                            "field": "position"
                        },
                        {
                            "field": "alt"
                        }
                    ],
                    "_source": "position",
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
        },
        "query": {
            "bool": {
                "filter": [
                    {
                        "match_phrase": {
                            "serial.keyword": serial
                        }
                    }
                ]
            }
        }
    }
    results = es_request(query, "telm-*/_search", "POST")
    return results["aggregations"]["1"]["hits"]["hits"]


def getRecovered(serial):
    query = {
        "aggs": {
            "1": {
                "top_hits": {
                    "docvalue_fields": [
                        {
                            "field": "recovered_by.keyword"
                        }
                    ],
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
        },
        "query": {
            "bool": {
                "filter": [
                    {
                        "match_phrase": {
                            "serial.keyword": serial
                        }
                    },
                    {
                        "match_phrase": {
                            "recovered": True
                        }
                    },
                ]
            }
        }
    }
    results = es_request(query, "recovered*/_search", "POST")
    return results["aggregations"]["1"]["hits"]["hits"]


def put(event, context):
    if "isBase64Encoded" in event and event["isBase64Encoded"] == True:
        event["body"] = base64.b64decode(event["body"])
    if (
        "content-encoding" in event["headers"]
        and event["headers"]["content-encoding"] == "gzip"
    ):
        event["body"] = zlib.decompress(event["body"], 16 + zlib.MAX_WBITS)
    time_delta = None
    if "date" in event["headers"]:
        try:
            time_delta_header = event["headers"]["date"]
            time_delta = (
                datetime.datetime(*parsedate(time_delta_header)[:7])
                - datetime.datetime.utcnow()
            ).total_seconds()
        except:
            pass

    recovered = json.loads(event["body"])

    if "datetime" not in recovered:
        recovered["datetime"] = datetime.datetime.now().isoformat()

    sonde_last_data = getSonde(recovered["serial"])

    if recovered["serial"] == "":
        return {"statusCode": 400, "body":  json.dumps({"message": "serial cannot be empty"})}

    if len(sonde_last_data) == 0:
        return {"statusCode": 400, "body":  json.dumps({"message": "serial not found in db"})}

    already_recovered = getRecovered(recovered["serial"])
    if len(already_recovered) != 0:
        recovered_by = already_recovered[0]['fields']['recovered_by.keyword'][0]
        return {"statusCode": 400, "body": json.dumps({"message": f"Already recovered by {recovered_by}"})}

    recovered['position'] = [recovered['lon'], recovered['lat']]

    result = es_request(recovered, "recovered/_doc", "POST")

    # add in elasticsearch extra position field
    return {"statusCode": 200, "body": json.dumps({"message": "telm logged. Have a good day ^_^"})}


def get(event, context):
    filters = []
    last = 259200
    serial = None
    lat = None
    lon = None
    distance = None

    # grab query parameters
    if "queryStringParameters" in event:
        if "last" in event["queryStringParameters"]:
            last = int(event['queryStringParameters']['last'])
        if "serial" in event["queryStringParameters"]:
            serial = event['queryStringParameters']['serial']
        if "lat" in event["queryStringParameters"]:
            lat = float(event["queryStringParameters"]['lat'])
        if "lon" in event["queryStringParameters"]:
            lon = float(event["queryStringParameters"]['lon'])
        if "distance" in event["queryStringParameters"]:
            distance = int(event["queryStringParameters"]['distance'])

    if last != 0:
        filters.append(
            {
                "range": {
                    "datetime": {
                        "gte": f"now-{last}s",
                        "lte": "now",
                    }
                }
            }
        )
    if serial:
        filters.append(
            {
                "match_phrase": {
                    "serial.keyword": serial
                }
            }
        )
    if lat and lon and distance:
        filters.append(
            {
                "geo_distance": {
                    "distance": f"{distance}m",
                    "position": {
                        "lat": lat,
                        "lon": lon,
                    },
                }
            }
        )

    query = {
        "query": {
            "bool": {
                "filter": filters
            }
        },
        "aggs": {
            "2": {
                "terms": {
                    "field": "serial.keyword",
                    "order": {
                        "2-orderAgg": "desc"
                    },
                    "size": 500
                },
                "aggs": {
                    "2-orderAgg": {
                        "max": {
                            "field": "datetime"
                        },
                    },
                    "1": {
                        "top_hits": {
                            "_source": True,
                            "size": 1,
                            "sort": [
                                {
                                    "recovered": {
                                        "order": "desc"
                                    }
                                },
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
        }
    }
    results = es_request(query, "recovered*/_search", "POST")
    output = [x['1']['hits']['hits'][0]["_source"]
              for x in results['aggregations']['2']['buckets']]
    return {"statusCode": 200, "body": json.dumps(output)}


if __name__ == "__main__":
    payload = {
        "version": "2.0",
        "routeKey": "PUT /recovered",
        "rawPath": "/recovered",
        "rawQueryString": "",
        "headers": {
            "accept": "*/*",
            "accept-encoding": "deflate",
            "content-encoding": "",
            "content-length": "2135",
            "content-type": "application/json",
            "host": "api.v2.sondehub.org",
            "user-agent": "autorx-1.4.1-beta4",
            "x-amzn-trace-id": "Root=1-6015f571-6aef2e73165042d53fcc317a",
            "x-forwarded-for": "103.107.130.22",
            "x-forwarded-port": "443",
            "x-forwarded-proto": "https",
            "date": "Sun, 31 Jan 2021 00:21:45 GMT",
        },
        "requestContext": {
            "accountId": "143841941773",
            "apiId": "r03szwwq41",
            "domainName": "api.v2.sondehub.org",
            "domainPrefix": "api",
            "http": {
                "method": "PUT",
                "path": "/sondes/telemetry",
                "protocol": "HTTP/1.1",
                "sourceIp": "103.107.130.22",
                "userAgent": "autorx-1.4.1-beta4",
            },
            "requestId": "Z_NJvh0RoAMEJaw=",
            "routeKey": "PUT /sondes/telemetry",
            "stage": "$default",
            "time": "31/Jan/2021:00:10:25 +0000",
            "timeEpoch": 1612051825409,
        },
        "body": json.dumps({
            "datetime": "2021-06-06T01:10:07.629Z",
            "serial": "string",
            "lat": 0,
            "lon": 0,
            "alt": 0,
            "recovered": True,
            "recovered_by": "string",
            "description": "string"
        }),
        "isBase64Encoded": False,
    }
    # print(put(payload, {}))
    print(get(payload, {}))
