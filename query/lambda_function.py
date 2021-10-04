import boto3
import botocore.credentials
from botocore.awsrequest import AWSRequest
from botocore.endpoint import URLLib3Session
from botocore.auth import SigV4Auth
import json
import os
from datetime import datetime, timedelta, timezone
import sys, traceback
import re
import html
import base64
import gzip
from io import BytesIO


HOST = os.getenv("ES")
# get current sondes, filter by date, location


def get_sondes(event, context):
    path = "telm-*/_search"
    payload = {
        "aggs": {
            "2": {
                "terms": {
                    "field": "serial.keyword",
                    "order": {"_key": "desc"},
                    "size": 10000,
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
        "query": {"bool": {"filter": [{"match_all": {}}]}},
    }

    # add filters
    if "queryStringParameters" in event:
        if "last" in event["queryStringParameters"]:
            payload["query"]["bool"]["filter"].append(
                {
                    "range": {
                        "datetime": {
                            "gte": f"now-{int(event['queryStringParameters']['last'])}s",
                            "lte": "now+1m",
                        }
                    }
                }
            )
        else:
            payload["query"]["bool"]["filter"].append(
                {"range": {"datetime": {"gte": "now-1d", "lte": "now+1m"}}}
            )

        if (
            "lat" in event["queryStringParameters"]
            and "lon" in event["queryStringParameters"]
            and "distance" in event["queryStringParameters"]
        ):
            payload["query"]["bool"]["filter"].append(
                {
                    "geo_distance": {
                        "distance": f"{int(event['queryStringParameters']['distance'])}m",
                        "position": {
                            "lat": float(event["queryStringParameters"]["lat"]),
                            "lon": float(event["queryStringParameters"]["lon"]),
                        },
                    }
                }
            )
    else:
        payload["query"]["bool"]["filter"].append(
                {"range": {"datetime": {"gte": "now-1d", "lte": "now+1m"}}}
        )
        
    results = es_request(payload, path, "POST")
    buckets = results["aggregations"]["2"]["buckets"]
    sondes = {
        bucket["1"]["hits"]["hits"][0]["_source"]["serial"]: bucket["1"]["hits"][
            "hits"
        ][0]["_source"]
        for bucket in buckets
    }
    return json.dumps(sondes)


def get_telem(event, context):

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
    duration_query = "3h"
    requested_time = datetime.now(timezone.utc)

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

    (duration, interval) = durations[duration_query]
    if "serial" in event["queryStringParameters"]:
        interval = 1
    lt = requested_time + timedelta(0, 1)
    gte = requested_time - timedelta(0, duration)

    path = f"telm-{lt.year:2}-{lt.month:02},telm-{gte.year:2}-{gte.month:02}/_search"
    payload = {
        "timeout": "30s",
        "size": 0,
        "aggs": {
            "2": {
                "terms": {
                    "field": "serial.keyword",
                    "order": {"_key": "desc"},
                    "size": 10000,
                },
                "aggs": {
                    "3": {
                        "date_histogram": {
                            "field": "datetime",
                            "fixed_interval": f"{str(interval)}s",
                            "min_doc_count": 1,
                        },
                        "aggs": {
                            "1": {
                                "top_hits": {
                                    # "docvalue_fields": [
                                    #     {"field": "position"},
                                    #     {"field": "alt"},
                                    #     {"field": "datetime"},
                                    # ],
                                    # "_source": "position",
                                    "size": 10 if (duration == 0 ) else 1,
                                        "sort": [
                                                {"datetime": {"order": "desc"}},
                                                {"pressure": {"order": "desc","mode" : "median"}}
                                            ],
                                }
                            }
                        },
                    }
                },
            }
        },
        "query": {
            "bool": {
                "must_not": [{"match_phrase": {"software_name": "SondehubV1"}}, {"match_phrase": {"serial": "xxxxxxxx"}}],
                "filter": [
                    {"match_all": {}},
                    {
                        "range": {
                            "datetime": {"gte": gte.isoformat(), "lt": lt.isoformat()}
                        }
                    },
                ]
            }
        },
    }
    if "queryStringParameters" in event:
        if "serial" in event["queryStringParameters"]:
            payload["query"]["bool"]["filter"].append(
                {
                    "match_phrase": {
                        "serial": str(event["queryStringParameters"]["serial"])
                    }
                }
            )
    results = es_request(payload, path, "POST")
    output = {
        sonde["key"]: {
            data["key_as_string"]: dict(data["1"]["hits"]["hits"][0]["_source"],
                uploaders=[ #add additional uploader information
                    {key:value for key,value in uploader['_source'].items() if key in ["snr","rssi","uploader_callsign"]}
                    for uploader in data["1"]["hits"]["hits"] 
                ])
            for data in sonde["3"]["buckets"]
        }
        for sonde in results["aggregations"]["2"]["buckets"]
    }

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


def get_listener_telemetry(event, context):

    durations = {  # ideally we shouldn't need to predefine these, but it's a shit load of data and we don't need want to overload ES
 "3d": (259200, 2400),  # 3d, 20m
        "1d": (86400, 2400),  # 1d, 10m
        "12h": (43200, 1200),  # 1d, 10m
        "6h": (21600, 300),  # 6h, 1m
        "3h": (10800, 120),  # 3h, 10s
        "1h": (3600, 120),
        "30m": (1800, 30),
        "1m": (60, 1),
        "15s": (15, 1),
        "0": (0, 1)
    }
    duration_query = "3h"
    requested_time = datetime.now(timezone.utc)

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

    (duration, interval) = durations[duration_query]
    if "uploader_callsign" in event["queryStringParameters"]:
        interval = 1
    lt = requested_time
    gte = requested_time - timedelta(0, duration)

    path = "listeners-*/_search"
    payload = {
        "timeout": "30s",
        "aggs": {
            "2": {
                "terms": {
                    "field": "uploader_callsign.keyword",
                    "order": {"_key": "desc"},
                    "size": 10000,
                },
                "aggs": {
                    "3": {
                        "date_histogram": {
                            "field": "ts",
                            "fixed_interval": f"{str(interval)}s",
                            "min_doc_count": 1,
                        },
                        "aggs": {
                            "1": {
                                "top_hits": {
                                    # "docvalue_fields": [
                                    #     {"field": "position"},
                                    #     {"field": "alt"},
                                    #     {"field": "datetime"},
                                    # ],
                                    # "_source": "position",
                                    "size": 1,
                                    "sort": [{"ts": {"order": "desc"}}],
                                }
                            }
                        },
                    }
                },
            }
        },
        "query": {
            "bool": {
                "filter": [
                    {"match_all": {}},
                    {
                        "range": {
                            "ts": {"gte": gte.isoformat(), "lt": lt.isoformat()}
                        }
                    },
                ]
            }
        },
    }
    if "queryStringParameters" in event:
        if "uploader_callsign" in event["queryStringParameters"]:
            payload["query"]["bool"]["filter"].append(
                {
                    "match_phrase": {
                        "uploader_callsign": str(event["queryStringParameters"]["uploader_callsign"])
                    }
                }
            )
    results = es_request(payload, path, "POST")
    output = {
        sonde["key"]: {
            data["key_as_string"]: data["1"]["hits"]["hits"][0]["_source"]
            for data in sonde["3"]["buckets"]
        }
        for sonde in results["aggregations"]["2"]["buckets"]
    }

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

def get_sites(event, context):

    path = "sites/_search"
    payload = {
        "version": True,
        "size": 10000,
        "_source": {
            "excludes": []
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
    if "queryStringParameters" in event:
        if "station" in event["queryStringParameters"]:
            payload["query"]["bool"]["filter"].append(
                {
                    "match_phrase": {
                        "station": str(event["queryStringParameters"]["station"])
                    }
                }
            )
    results = es_request(payload, path, "POST")
    output = {x['_source']['station']: x['_source'] for x in results['hits']['hits']}

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

def get_listeners(event, context):

    path = "listeners-*/_search"
    payload = {
        "timeout": "30s",
        "aggs": {
            "2": {
                "terms": {
                    "field": "uploader_callsign.keyword",
                    "order": {"_key": "desc"},
                    "size": 500,
                },
                "aggs": {
                    "1": {
                        "top_hits": {
                            "_source": False,
                            "size": 1,
                            "docvalue_fields": [
                                "uploader_position_elk",
                                "uploader_alt",
                                "uploader_antenna.keyword",
                                "software_name.keyword",
                                "software_version.keyword",
                                "ts",
                            ],
                            "sort": [{"ts": {"order": "desc"}}],
                        }
                    }
                },
            }
        },
        "size": 0,
        "query": {
            "bool": {
                "must": [],
                "filter": [
                    {"match_all": {}},
                    {"exists": {"field": "uploader_position_elk"},},
                    {"exists": {"field": "uploader_antenna.keyword"},},
                    {"exists": {"field": "software_name.keyword"},},
                    {"exists": {"field": "software_version.keyword"},},
                    {"exists": {"field": "ts"},},
                    {
                        "range": {
                            "ts": {
                                "gte": "now-24h",
                                "lte": "now+1m",
                                "format": "strict_date_optional_time",
                            }
                        }
                    },
                    
                ],
                "should": [],
                "must_not": [
                    {"match_phrase": {"mobile": "true"}}, 
                ],
            }
        },
    }

    results = es_request(payload, path, "GET")

    output = [
        {
            "name": html.escape(listener["key"]),
            "tdiff_hours": (
                datetime.now(timezone.utc)
                - datetime.fromisoformat(
                    listener["1"]["hits"]["hits"][0]["fields"]["ts"][0].replace(
                        "Z", "+00:00"
                    )
                )
            ).seconds
            / 60
            / 60,
            "lon": float(
                listener["1"]["hits"]["hits"][0]["fields"]["uploader_position_elk"][0]
                .replace(" ", "")
                .split(",")[1]
            ),
            "lat": float(
                listener["1"]["hits"]["hits"][0]["fields"]["uploader_position_elk"][0]
                .replace(" ", "")
                .split(",")[0]
            ),
            "alt": float(listener["1"]["hits"]["hits"][0]["fields"]["uploader_alt"][0]) if "uploader_alt" in listener["1"]["hits"]["hits"][0]["fields"] else 0,
            "description": f"""\n
                <font size=\"-2\"><BR>\n
                    <B>Radio: {html.escape(listener["1"]["hits"]["hits"][0]["fields"]["software_name.keyword"][0])}-{html.escape(listener["1"]["hits"]["hits"][0]["fields"]["software_version.keyword"][0])}</B><BR>\n
                    <B>Antenna: </B>{html.escape(listener["1"]["hits"]["hits"][0]["fields"]["uploader_antenna.keyword"][0])}<BR>\n
                    <B>Last Contact: </B>{html.escape(listener["1"]["hits"]["hits"][0]["fields"]["ts"][0])} <BR>\n
                </font>\n
            """,
        }
        for listener in results["aggregations"]["2"]["buckets"]
    ]
    return json.dumps(output)


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
    SigV4Auth(boto3.Session().get_credentials(), "es", "us-east-1").add_auth(request)

    session = URLLib3Session()
    r = session.send(request.prepare())
    return json.loads(r.text)


if __name__ == "__main__":
    #print(get_sondes({"queryStringParameters":{"lat":"-32.7933","lon":"151.8358","distance":"5000", "last":"604800"}}, {}))
    # mode: 6hours
    # type: positions
    # format: json
    # max_positions: 0
    # position_id: 0
    # vehicles: RS_*;*chase
#     print(
#         datanew(
#             {
#              "queryStringParameters": {
# "mode": "single",
# "format": "json",
# "position_id": "S1443103-2021-07-20T12:46:19.040000Z"
#              }
#             },
#             {},
#         )
#     )
    print(get_sites({},{}))
    # print(
    #     get_telem(
    #         {
    #             "queryStringParameters": {
    #                 "duration": "3d",
    #                 "serial": "P4120469"
    #             }},{}
            
    #     )
    # )
    # print (
    #     get_chase(
    #         {"queryStringParameters": {
    #             "duration": "1d"
    #             }
    #         },
    #         {}
    #     )
    # )


    # print(
    #     datanew(
    #         {
    #          "queryStringParameters": {
    #              "type": "positions",
    #              "mode": "3hours",
    #              "position_id": "0"
    #          }
    #         },
    #         {},
    #     )
    # )
    # print(
    #     get_telem(
    #         {
    #             "queryStringParameters":{
    #                 # "serial": "S3210639",
    #                 "duration": "3h",
    #                # "datetime": "2021-07-26T06:49:29.001000Z"
    #             }
    #         }, {}
    #     )
    # )

