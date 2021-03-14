import boto3
import botocore.credentials
from botocore.awsrequest import AWSRequest
from botocore.endpoint import URLLib3Session
from botocore.auth import SigV4Auth
import json
import os
from datetime import datetime, timedelta, timezone
import sys, traceback

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
        "3h": (10800, 10),  # 3h, 10s
    }
    duration_query = "3h"
    requested_time = datetime.now()


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
        requested_time = datetime.fromisoformat(event["queryStringParameters"]["datetime"].replace("Z", "+00:00"))

    (duration, interval) = durations[duration_query]
   
    
    
    lt = requested_time
    gte = requested_time - timedelta(0,duration)


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
                    "3": {
                        "date_histogram": {
                            "field": "datetime",
                            "fixed_interval": f"{str(interval)}s",
                            "time_zone": "Australia/Brisbane",
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
                            "datetime": {
                                "gte": gte.isoformat(),
                                 "lt": lt.isoformat()
                            }
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
        "3days": (259200, 1200),  # 3d, 20m
        "1day": (86400, 600),  # 1d, 10m
        "12hours": (43200, 120),  # 12h, 2m
        "6hours": (21600, 60),  # 6h, 1m
        "3hours": (10800, 10),  # 3h, 10s
        "1hour": (3600, 10),  # 1h, 5s
    }
    duration_query = "1hour"
    requested_time = datetime.now()


    if event["queryStringParameters"]['type'] != 'positions':
        raise ValueError

    max_positions = int(event["queryStringParameters"]["max_positions"]) if "max_positions" in event["queryStringParameters"] else 10000

    if event["queryStringParameters"]["mode"] in durations:
        duration_query = event["queryStringParameters"]["mode"]
    else:
        return f"Duration must be either {', '.join(durations.keys())}"

    (duration, interval) = durations[duration_query]
    if "vehicles" in event["queryStringParameters"] and (event["queryStringParameters"]['vehicles'] != "RS_*;*chase" and event["queryStringParameters"]['vehicles'] != ""):
        interval = 5

    if event["queryStringParameters"]["position_id"] != "0":
        requested_time = datetime.fromisoformat(event["queryStringParameters"]["position_id"].replace("Z", "+00:00"))
        lt = datetime.now()
        gte = requested_time
    else:
        lt = datetime.now()
        gte = datetime.now() - timedelta(0,duration)

    
   


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
                    "3": {
                        "date_histogram": {
                            "field": "datetime",
                            "fixed_interval": f"{str(interval)}s",
                            "time_zone": "Australia/Brisbane",
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
            }
        },
        "query": {
            "bool": {
                "filter": [
                    {"match_all": {}},
                    {
                        "range": {
                            "datetime": {
                                "gte": gte.isoformat(),
                                 "lt": lt.isoformat()
                            }
                        }
                    },
                ]
            }
        },
    }
    if "vehicles" in event["queryStringParameters"] and event["queryStringParameters"]['vehicles'] != "RS_*;*chase" and event["queryStringParameters"]['vehicles']  != "":
        payload["query"]["bool"]["filter"].append(
            {
                "match_phrase": {
                    "serial": str(event["queryStringParameters"]["vehicles"])
                }
            }
        )
    results = es_request(payload, path, "POST")

    output = {
                "positions": {
                    "position": []
                }
            }

    for sonde in results["aggregations"]["2"]["buckets"]:
        for frame in sonde["3"]["buckets"]:
            try:
                frame_data = frame['1']['hits']['hits'][0]['_source']
                frequency = f'{frame_data["frequency"]} MHz' if "frequency" in frame_data else ""
                pressure = f'{frame_data["pressure"]}hPa' if "pressure" in frame_data else ""
                bt = f'BT {frame_data["burst_timer"]}' if "burst_timer" in frame_data else ""
                batt = f'{frame_data["batt"]}V' if "batt" in frame_data else ""
                subtype = frame_data["subtype"] if "subtype" in frame_data else ""
                data = {
                     "comment": f"{subtype} {frame_data['serial']} {frequency} {pressure} {bt} {batt}"
                }
                if "temp" in frame_data:
                    data["temperature_external"] = frame_data["temp"]
                if  "humidity" in frame_data:
                    data["humidity"] = frame_data["humidity"]
                if "pressure" in frame_data:
                    data["pressure"] = frame_data["pressure"]
                if "sats" in frame_data:
                    data["sats"] = frame_data["sats"]
                if "batt" in frame_data:
                    data["batt"] = frame_data["batt"]
                output["positions"]["position"].append({
                    "position_id": f'{frame_data["serial"]}-{frame_data["datetime"]}',
                    "mission_id": "0",
                    "vehicle": frame_data["serial"],
                    "server_time": frame_data["datetime"],
                    "gps_time": frame_data["datetime"],
                    "gps_lat": frame_data["lat"],
                    "gps_lon": frame_data["lon"],
                    "gps_alt": frame_data["alt"],
                    "gps_heading": frame_data["heading"] if "heading" in frame_data else "",
                    "gps_speed": frame_data["vel_h"],
                    "picture": "",
                    "temp_inside": "",
                    "data": data,
                    "callsign": frame_data["uploader_callsign"],
                    "sequence": "0"
                })
            except:
                pass
    output["positions"]["position"] = sorted(output["positions"]["position"], key=lambda k: k['position_id']) 
    return json.dumps(output)


def get_listeners(event, context):

    path = "telm-*/_search"
    payload = {
        "aggs": {
            "2": {
            "terms": {
                "field": "uploader_callsign.keyword",
                "order": {
                "_key": "desc"
                },
                "size": 500
            },
            "aggs": {
                "1": {
                "top_hits": {
                    "_source": False,
                    "size": 1,
                    "docvalue_fields": ["uploader_position", "uploader_alt", "uploader_antenna.keyword","software_name.keyword", "software_version.keyword", "datetime" ], 
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
        "query": {
            "bool": {
            "must": [],
            "filter": [
                {
                "match_all": {}
                },
                {
                    "exists": {
                        "field": "uploader_position"
                    },
                },
                {
                    "exists": {
                        "field": "uploader_alt"
                    },
                },
                {
                    "exists": {
                        "field": "uploader_antenna.keyword"
                    },
                },
                
                {
                    "exists": {
                        "field": "software_name.keyword"
                    },
                },
                 {
                    "exists": {
                        "field": "software_version.keyword"
                    },
                },
                {
                    "exists": {
                        "field": "datetime"
                    },
                },
                {
                "range": {
                    "datetime": {
                    "gte": "now-7d",
                    "lte": "now",
                    "format": "strict_date_optional_time"
                    }
                }
                }
            ],
            "should": [],
            "must_not": [
                {
                "match_phrase": {
                    "type": "SondehubV1"
                }
                }
            ]
            }
        }
    }
  
    results = es_request(payload, path, "GET")
    
    output = [
        {
            "name": listener['key'],
            "tdiff_hours": (datetime.now(timezone.utc) - datetime.fromisoformat(listener["1"]["hits"]["hits"][0]["fields"]['datetime'][0].replace("Z", "+00:00"))).seconds/60/60,
            "lon": float(listener["1"]["hits"]["hits"][0]["fields"]['uploader_position'][0].replace(" ","").split(",")[1]),
            "lat": float(listener["1"]["hits"]["hits"][0]["fields"]['uploader_position'][0].replace(" ","").split(",")[0]),
            "alt": float(listener["1"]["hits"]["hits"][0]["fields"]['uploader_alt'][0]),
            "description": f"""\n
                <font size=\"-2\"><BR>\n
                    <B>Radio: {listener["1"]["hits"]["hits"][0]["fields"]["software_name.keyword"][0]}-{listener["1"]["hits"]["hits"][0]["fields"]["software_version.keyword"][0]}</B><BR>\n
                    <B>Antenna: </B>{listener["1"]["hits"]["hits"][0]["fields"]["uploader_antenna.keyword"][0]}<BR>\n
                    <B>Last Contact: </B>{listener["1"]["hits"]["hits"][0]["fields"]["datetime"][0]} <BR>\n
                </font>\n
            """
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
           {"queryStringParameters":{
               "mode": "1day",
                "type": "positions",
                "format": "json",
                "max_positions": "0",
                "position_id": "0",
                "vehicles": ""
           }},{}
        )
    )
