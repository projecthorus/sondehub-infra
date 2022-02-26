import json
from datetime import datetime, timedelta, timezone
import base64
import gzip
from io import BytesIO
import es

def get(event, context):
    path = "ham-telm-*/_search"
    payload = {
        "size": 0,
        "aggs": {
            "2": {
                "terms": {
                    "field": "payload_callsign.keyword",
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
                            "gte": f"now-{abs(int(event['queryStringParameters']['last']))}s",
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
    try:
        results = es.request(json.dumps(payload), path, "POST")
    except:
        print(json.dumps(event))
        raise
    buckets = results["aggregations"]["2"]["buckets"]
    sondes = {
        bucket["1"]["hits"]["hits"][0]["_source"]["payload_callsign"]: bucket["1"]["hits"][
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
        "6h": (21600, 1),  # 6h, 1m
        "3h": (10800, 1),  # 3h, 10s
        "1h": (3600, 1),
        "30m": (1800, 1),
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
    if "payload_callsign" in event["queryStringParameters"]:
        interval = 1
    lt = requested_time + timedelta(0, 1)
    gte = requested_time - timedelta(0, duration)

    path = f"ham-telm-{lt.year:2}-{lt.month:02},telm-{gte.year:2}-{gte.month:02}/_search"
    payload = {
        "timeout": "30s",
        "size": 0,
        "aggs": {
            "2": {
                "terms": {
                    "field": "payload_callsign.keyword",
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
                                    "size": 10,
                                        "sort": [
                                                {"datetime": {"order": "desc"}}
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
                "must_not": [{"match_phrase": {"software_name": "SondehubV1"}}, {"match_phrase": {"payload_callsign": "xxxxxxxx"}}],
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
        if "payload_callsign" in event["queryStringParameters"]:
            payload["query"]["bool"]["filter"].append(
                {
                    "match_phrase": {
                        "payload_callsign": str(event["queryStringParameters"]["payload_callsign"])
                    }
                }
            )
    results = es.request(json.dumps(payload), path, "POST")
    output = {
        sonde["key"]: {
            data["key_as_string"]: dict(data["1"]["hits"]["hits"][0]["_source"],
                uploaders=[ #add additional uploader information
                    {key:value for key,value in uploader['_source'].items() if key in ["snr","rssi","uploader_callsign", "frequency"]}
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

