import json
from datetime import datetime, timedelta, timezone
import base64
import gzip
from io import BytesIO, StringIO
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
        "366d": (31622400, 14000),
        "186d": (16070400, 3600),
        "31d": (2678400, 300),
        "7d": (604800, 120),
        "3d": (259200, 15), 
        "1d": (86400, 1), 
        "12h": (43200, 1),  
        "6h": (21600, 1), 
        "3h": (10800, 1), 
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

    path = f"ham-telm-{lt.year:2}-{lt.month:02},ham-telm-{gte.year:2}-{gte.month:02}/_search"
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
                "minimum_should_match": 1,
                "must_not": [{"match_phrase": {"software_name": "SondehubV1"}}, {"match_phrase": {"payload_callsign": "xxxxxxxx"}}],
                    "should": [
                        {
                        "bool": {
                            "must": [
                                {
                                    "exists": {
                                    "field": "sats"
                                    }
                                },
                                {
                                "range": {
                                        "sats": {
                                            "gte": 1,
                                            "lt": None
                                        }
                                    }
                                }
                            ]
                        }
                        },
                        {
                            "bool": {
                                "must_not": [
                                    {
                                        "exists": {
                                        "field": "sats"
                                        }
                                    }
                                ]
                            }
                        }
                    ],
                "filter": [
                    {"match_all": {}},
                    {
                        "range": {
                            "datetime": {"gte": gte.isoformat(), "lt": lt.isoformat()}
                        }
                    }
                ]
            }
        },
    }
    if "queryStringParameters" in event:
        if "payload_callsign" in event["queryStringParameters"]:
            payloads = str(event["queryStringParameters"]["payload_callsign"]).split(",")
            payload["query"]["bool"]["must"] = {
                "bool": {
                    "should": [ {"match_phrase": {"payload_callsign": x}} for x in payloads ]
                }
            }
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
def get_telem_full(event, context):
   
    

    if (
        "queryStringParameters" in event
        and "last" in event["queryStringParameters"]
    ):
        last = int(event["queryStringParameters"]["last"])
    else:
        last = 21600 # 6 hours
    
    if (
        "queryStringParameters" in event
        and "datetime" in event["queryStringParameters"]
    ):
        try:
            requested_time = datetime.fromisoformat(
                event["queryStringParameters"]["datetime"].replace("Z", "+00:00")
            )
        except: # might be in unix time
            requested_time = datetime.utcfromtimestamp(float(event["queryStringParameters"]["datetime"]))
    else:
        requested_time = datetime.now(timezone.utc)


    lt = requested_time + timedelta(0, 1)
    gte = requested_time - timedelta(0, last)

    path = f"ham-telm-*/_search"
    payload = {
        "timeout": "30s",
        "size": 10000,
        "query": {
            "bool": {
                "minimum_should_match": 1,
                "must_not": [{"match_phrase": {"software_name": "SondehubV1"}}, {"match_phrase": {"payload_callsign": "xxxxxxxx"}}],
                    "should": [
                        {
                        "bool": {
                            "must": [
                                {
                                    "exists": {
                                    "field": "sats"
                                    }
                                },
                                {
                                "range": {
                                        "sats": {
                                            "gte": 1,
                                            "lt": None
                                        }
                                    }
                                }
                            ]
                        }
                        },
                        {
                            "bool": {
                                "must_not": [
                                    {
                                        "exists": {
                                        "field": "sats"
                                        }
                                    }
                                ]
                            }
                        }
                    ],
                "filter": [
                    {"match_all": {}},
                    {
                        "range": {
                            "datetime": {"gte": gte.isoformat(), "lt": lt.isoformat()}
                        }
                    }
                ]
            }
        },
    }
    payload["query"]["bool"]["filter"].append(
        {
            "match_phrase": {
                "payload_callsign": str(event["pathParameters"]["payload_callsign"])
            }
        }
    )
    data = []
    response = es.request(json.dumps(payload), path, "POST", params={"scroll": "1m"})
    scroll_id = response['_scroll_id']
    scroll_ids = [scroll_id]
    data += [ x["_source"] for x in response['hits']['hits']]


    while response['hits']['hits']:
        response = es.request(json.dumps({"scroll": "1m", "scroll_id": scroll_id }),
                          "_search/scroll", "POST")
        scroll_id = response['_scroll_id']
        scroll_ids.append(scroll_id)
        data += [ x["_source"] for x in response['hits']['hits']]
    for scroll_id in scroll_ids: # clean up scrolls
        try:
            scroll_delete = es.request(json.dumps({"scroll_id": scroll_id }),
                                "_search/scroll", "DELETE")
            print(scroll_delete)
        except RuntimeError:
            pass

    filename = f'{event["pathParameters"]["payload_callsign"]}.json'
    content_type = "application/json"
    # convert to CSV if requested
    if (
        "queryStringParameters" in event
        and "format" in event["queryStringParameters"]
        and event["queryStringParameters"]['format'] == "csv"
    ):
        import csv
        content_type = "text/csv"
        filename = f'{event["pathParameters"]["payload_callsign"]}.csv'
        csv_keys = list(set().union(*(d.keys() for d in data)))
        csv_keys.remove("datetime")
        csv_keys.insert(0,"datetime") # datetime should be at the front of the CSV
        csv_output = StringIO(newline='')
        fc = csv.DictWriter(csv_output, fieldnames=csv_keys)
        fc.writeheader()
        fc.writerows(data)
        
        data = csv_output.getvalue()
    elif (
        "queryStringParameters" in event
        and "format" in event["queryStringParameters"]
        and event["queryStringParameters"]['format'] == "kml"
    ):
        content_type = "application/vnd.google-earth.kml+xml"
        filename = f'{event["pathParameters"]["payload_callsign"]}.kml'

        # Extract some basic flight info for use in KML Metadata
        callsign = str(event["pathParameters"]["payload_callsign"])
        start_datetime = gte.isoformat()

        # Only get unique date/time data.
        # This results in a much shorter dictionary.
        _temp_data = {}
        for _telem in data:
            _temp_data[_telem['datetime']] = f"{float(_telem['lon']):.6f},{float(_telem['lat']):.6f},{float(_telem['alt']):.1f}\n"

        # For a KML output, the data *must* be sorted, else the KML LineString becomes a complete mess.
        # Get the keys from the dictionary generated above, and sort them.
        data_keys = list(_temp_data.keys())
        data_keys.sort()

        # Now generate the LineString data (lon,lat,alt)
        # This could possibly done with a .join, but I suspect that wont be much more efficient.
        kml_coords = ""
        for _key in data_keys:
            kml_coords += _temp_data[_key]

        # Generate the output KML. 
        # This is probably the simplest way of handling this without bringing in
        # any other libraries.
        kml_out = f"""
        <kml:Document xmlns:kml="http://www.opengis.net/kml/2.2">
        <kml:visibility>1</kml:visibility>
        <kml:Folder id="{callsign}">
            <kml:name>{start_datetime} {callsign}</kml:name>
            <kml:description>Flight Path</kml:description>
            <kml:visibility>1</kml:visibility>
            <kml:Placemark id="Flight Path ID">
                <kml:name>{start_datetime} {callsign}</kml:name>
                <kml:visibility>1</kml:visibility>
                <kml:Style><kml:LineStyle>
                <kml:color>aaffffff</kml:color>
                <kml:width>2.0</kml:width>
                </kml:LineStyle>
                <kml:PolyStyle>
                <kml:color>20000000</kml:color>
                <kml:fill>1</kml:fill>
                <kml:outline>1</kml:outline>
                </kml:PolyStyle></kml:Style>
                <kml:LineString>
                    <kml:extrude>1</kml:extrude>
                    <kml:altitudeMode>absolute</kml:altitudeMode>
                    <kml:coordinates>
        {kml_coords}
                    </kml:coordinates>
                </kml:LineString>
        </kml:Placemark>
        </kml:Folder>
        </kml:Document>
        """

        # Finally replace the data with the kml data
        data = kml_out
    else:
        data = json.dumps(data)

    compressed = BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode='w') as f:
        f.write(data.encode('utf-8'))
    
    gzippedResponse = compressed.getvalue()
    body = base64.b64encode(gzippedResponse).decode()
    if len(body) > (1024 * 1024 * 6) - 1000 : # check if payload is too big
        content_type = "text/plain"
        body = "Output is too large, try a smaller time frame"

    return {
            "body": body,
            "isBase64Encoded": True,
            "statusCode": 200,
            "headers": {
                "Content-Encoding": "gzip",
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": content_type
            }
            
        }

def get_listener_telemetry(event, context):

    durations = {  # ideally we shouldn't need to predefine these, but it's a shit load of data and we don't need want to overload ES
 "3d": (259200, 1),  # 3d, 20m
        "1d": (86400, 1),  # 1d, 10m
        "12h": (43200, 1),  # 1d, 10m
        "6h": (21600, 1),  # 6h, 1m
        "3h": (10800, 1),  # 3h, 10s
        "1h": (3600, 1),
        "30m": (1800, 1),
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
    if "queryStringParameters" in event and "uploader_callsign" in event["queryStringParameters"]:
        interval = 1
    lt = requested_time
    gte = requested_time - timedelta(0, duration)

    path = "ham-listeners-*/_search"
    payload = {
        "size": 0,
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
                    {"exists": { "field": "uploader_position"}},
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
    results = es.request(json.dumps(payload), path, "POST")
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