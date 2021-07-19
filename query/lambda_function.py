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
                            "lte": "now",
                        }
                    }
                }
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
    # if the user doesn't specify a range we should add one - 24 hours is probably a good start
    if "range" not in payload["query"]["bool"]["filter"]:
        payload["query"]["bool"]["filter"].append(
            {"range": {"datetime": {"gte": "now-1d", "lte": "now"}}}
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
        "6h": (21600, 60),  # 6h, 1m
        "3h": (10800, 15),  # 3h, 10s
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

    lt = requested_time
    gte = requested_time - timedelta(0, duration)

    path = "telm-*/_search"
    payload = {
        "timeout": "30s",
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
                                    "size": 1,
                                    "sort": [{"datetime": {"order": "desc"}}],
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
            data["key_as_string"]: data["1"]["hits"]["hits"][0]["_source"]
            for data in sonde["3"]["buckets"]
        }
        for sonde in results["aggregations"]["2"]["buckets"]
    }
    return json.dumps(output)


def datanew(event, context):
    durations = {  # ideally we shouldn't need to predefine these, but it's a shit load of data and we don't need want to overload ES
        "3days": (259200, 1800),  # 3d, 20m
        "1day": (86400, 900),  # 1d, 10m
        "12hours": (43200, 480),  # 12h, 2m
        "6hours": (21600, 180),  # 6h, 1m
        "3hours": (10800, 90),  # 3h, 10s
        "1hour": (3600, 30),  # 1h, 5s
    }
    duration_query = "1hour"
    requested_time = datetime.now(timezone.utc)

    max_positions = (
        int(event["queryStringParameters"]["max_positions"])
        if "max_positions" in event["queryStringParameters"]
        else 10000
    )

    if event["queryStringParameters"]["mode"] in durations:
        duration_query = event["queryStringParameters"]["mode"]
        (duration, interval) = durations[duration_query]
    elif event["queryStringParameters"]["mode"] == "single":
        duration = 259200
        interval = 1
    else:
        return f"Duration must be either {', '.join(durations.keys())}"

    
    if "vehicles" in event["queryStringParameters"] and (
        event["queryStringParameters"]["vehicles"] != "RS_*;*chase"
        and event["queryStringParameters"]["vehicles"] != ""
    ):
        interval = 2


    if event["queryStringParameters"]["position_id"] != "0":
        if event["queryStringParameters"]["mode"] == "single":
            position_id = event["queryStringParameters"]["position_id"]
            matches = re.search("(.+)-(\d{4}-\d{2}-\d{2}\w\d{2}:\d{2}:\d{2}.\d+)Z",position_id).groups()
            matched_time = matches[1].replace("Z", "+00:00")
            matched_vehicle = matches[0]
            requested_time = datetime.fromisoformat(matched_time)
            lt = requested_time + timedelta(seconds=duration)
            gte = requested_time

        else:
            requested_time = datetime.fromisoformat(
                event["queryStringParameters"]["position_id"].replace("Z", "+00:00")
            )
            lt = requested_time + timedelta(seconds=duration)
            gte = requested_time
        
    elif event["queryStringParameters"]["mode"] == "single":
        return f"Single requires a position id specified"
    else:
        lt = datetime.now(timezone.utc)
        gte = datetime.now(timezone.utc) - timedelta(0, duration)
    output = {"positions": {"position": []}}
    if "chase_only" not in event["queryStringParameters"] or event["queryStringParameters"]["chase_only"] != "true":
        path = "telm-*/_search"
        payload = {
            "timeout": "30s",
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
                                        "size": 5,
                                        "sort": [
                                                {"datetime": {"order": "desc"}},
                                                {"pressure": {"order": "desc","mode" : "median"}},
                                                {"humidity": {"order": "desc","mode" : "median"}},
                                                {"temp": {"order": "desc","mode" : "median"}},
                                                {"alt": {"order": "desc","mode" : "median"}}
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
                    "filter": [
                        {"match_all": {}},
                        {
                            "range": {
                                "datetime": {"gte": gte.isoformat(), "lte": lt.isoformat()}
                            }
                        },
                    ],
                    "must_not": [{"match_phrase": {"software_name": "SondehubV1"}}, {"match_phrase": {"serial": "xxxxxxxx"}}],
                }
            },
        }
        if (
            "vehicles" in event["queryStringParameters"]
            and event["queryStringParameters"]["vehicles"] != "RS_*;*chase"
            and event["queryStringParameters"]["vehicles"] != ""
        ):
            payload["query"]["bool"]["filter"].append(
                {
                    "match_phrase": {
                        "serial": str(event["queryStringParameters"]["vehicles"])
                    }
                }
            )
        if event["queryStringParameters"]["mode"] == "single":
            payload["query"]["bool"]["filter"].append(
                {
                    "match_phrase": {
                        "serial": matched_vehicle
                    }
                }
            )
        results = es_request(payload, path, "POST")



        for sonde in results["aggregations"]["2"]["buckets"]:
            for frame in sonde["3"]["buckets"]:
                try:
                    frame_data = frame["1"]["hits"]["hits"][0]["_source"]
                    uploaders = {}
                    
                    # Use subtype if it exists, else just use the basic type.
                    if "subtype" in frame_data:
                        _type = html.escape(frame_data["subtype"])
                    else:
                        _type = html.escape(frame_data["type"])

                    data = {
                        "manufacturer": html.escape(frame_data['manufacturer']),
                        "type": html.escape(_type)
                    }

                    if "temp" in frame_data:
                        data["temperature_external"] = frame_data["temp"]

                    if "humidity" in frame_data:
                        data["humidity"] = frame_data["humidity"]

                    if "pressure" in frame_data:
                        data["pressure"] = frame_data["pressure"]

                    if "sats" in frame_data:
                        data["sats"] = frame_data["sats"]

                    if "batt" in frame_data:
                        data["batt"] = frame_data["batt"]

                    if "burst_timer" in frame_data:
                        data["burst_timer"] = frame_data["burst_timer"]

                    if "frequency" in frame_data:
                        data["frequency"] = frame_data["frequency"]

                    # May need to revisit this, if the resultant strings are too long.
                    if "xdata" in frame_data:
                        data["xdata"] = html.escape(frame_data["xdata"])

                    output["positions"]["position"].append(
                        {
                            "position_id": html.escape(f'{frame_data["serial"]}-{frame_data["datetime"]}'),
                            "mission_id": "0",
                            "vehicle": html.escape(frame_data["serial"]),
                            "server_time": html.escape(frame_data["datetime"]),
                            "gps_time": html.escape(frame_data["datetime"]),
                            "gps_lat": frame_data["lat"],
                            "gps_lon": frame_data["lon"],
                            "gps_alt": frame_data["alt"],
                            "gps_heading": frame_data["heading"]
                            if "heading" in frame_data
                            else "",
                            "gps_speed": frame_data["vel_h"] if "vel_h" in frame_data else "",
                            "type": html.escape(_type),
                            "picture": "",
                            "temp_inside": "",
                            "data": data,
                            "callsign": uploaders,
                            "sequence": "0",
                        }
                    )
                except:
                    traceback.print_exc(file=sys.stdout)
            output["positions"]["position"][-1]["callsign"] = {
                html.escape(x["_source"]['uploader_callsign']) : {
                    "snr" : x["_source"]["snr"] if "snr" in x["_source"]  else None,
                    "rssi" : x["_source"]["rssi"] if "rssi" in x["_source"] else None
                }
                for x in frame["1"]["hits"]["hits"]
            }

    # get chase cars

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
                        "match_phrase": {
                            "mobile": True
                        }
                    },
                    {
                        "range": {
                            "ts": {"gte": gte.isoformat(), "lt": lt.isoformat()}
                        }
                    },
                ]
            }
        },
    }

    path = "listeners-*/_search"

    # {"position_id":"82159921","mission_id":"0","vehicle":"KB9RKU_chase",
    # "server_time":"2021-04-09 06:28:55.109589","gps_time":"2021-04-09 06:28:54",
    # "gps_lat":"41.539648333","gps_lon":"-89.111862667","gps_alt":"231.6","gps_heading":"",
    # "gps_speed":"0","picture":"","temp_inside":"","data":{},"callsign":"","sequence":""}

    results = es_request(payload, path, "POST")
    
    for car in results["aggregations"]["2"]["buckets"]:
        for frame in car["3"]["buckets"]:
            try:
                frame_data = frame["1"]["hits"]["hits"][0]["_source"]

               
                data = {}
                # 
                output["positions"]["position"].append(
                    {
                        "position_id": html.escape(f'{frame_data["uploader_callsign"]}-{frame_data["ts"]}'),
                        "mission_id": "0",
                        "vehicle": html.escape(f'{frame_data["uploader_callsign"]}_chase'),
                        "server_time": html.escape(datetime.fromtimestamp(frame_data["ts"]/1000).isoformat()),
                        "gps_time": html.escape(datetime.fromtimestamp(frame_data["ts"]/1000).isoformat()),
                        "gps_lat": frame_data["uploader_position"][0],
                        "gps_lon": frame_data["uploader_position"][1],
                        "gps_alt": frame_data["uploader_position"][2],
                        "gps_heading": "",
                        "gps_speed": 0,
                        "picture": "",
                        "temp_inside": "",
                        "data": data,
                        "callsign": html.escape(frame_data["uploader_callsign"]),
                        "sequence": "",
                    }
                )
            except:
                traceback.print_exc(file=sys.stdout)
    
    output["positions"]["position"] = sorted(
        output["positions"]["position"], key=lambda k: k["position_id"]
    )
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
                                "lte": "now",
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
    headers = {"Host": HOST, "Content-Type": "application/json"}
    request = AWSRequest(
        method="POST", url=f"https://{HOST}/{path}", data=params, headers=headers
    )
    SigV4Auth(boto3.Session().get_credentials(), "es", "us-east-1").add_auth(request)

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
    print(
        datanew(
            {
             "queryStringParameters": {
                 "type": "positions",
                 "mode": "3hours",
                 "position_id": "0",
                 "vehicles": "T1240847"
             }
            },
            {},
        )
    )
    # print(
    #     get_listeners(
    #         {},{}
    #     )
    # )
