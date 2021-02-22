import boto3
import botocore.credentials
from botocore.awsrequest import AWSRequest
from botocore.endpoint import URLLib3Session
from botocore.auth import SigV4Auth
import json
import os
from datetime import datetime, timedelta, timezone
import sys, traceback
import http.client


HOST = os.getenv("ES")

def predict(event, context):

    path = "telm-*/_search"
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
                        "3": {
                        "date_histogram": {
                            "field": "datetime",
                            "fixed_interval": "30s"
                        },
                        "aggs": {
                            "1": {
                            "top_hits": {
                                "docvalue_fields": [
                                {
                                    "field": "alt"
                                }
                                ],
                                "_source": "alt",
                                "size": 1,
                                "sort": [
                                {
                                    "datetime": {
                                    "order": "desc"
                                    }
                                }
                                ]
                            }
                            },
                            "4": {
                            "serial_diff": {
                                "buckets_path": "4-metric"
                            }
                            },
                            "5": {
                            "top_hits": {
                                "docvalue_fields": [
                                {
                                    "field": "position"
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
                            },
                            "4-metric": {
                            "avg": {
                                "field": "alt"
                            }
                            }
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
                    "field": "@timestamp",
                    "format": "date_time"
                    },
                    {
                    "field": "datetime",
                    "format": "date_time"
                    },
                    {
                    "field": "log_date",
                    "format": "date_time"
                    },
                    {
                    "field": "time_received",
                    "format": "date_time"
                    },
                    {
                    "field": "time_server",
                    "format": "date_time"
                    },
                    {
                    "field": "time_uploaded",
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
                        "match_all": {}
                        },
                        {
                        "range": {
                            "datetime": {
                                    "gte": "now-1h",
                                    "lte": "now",
                            "format": "strict_date_optional_time"
                            }
                        }
                        }
                    ],
                    "should": [],
                    "must_not": []
                    }
                }
            }
    if "queryStringParameters" in event:
        if "vehicles" in event["queryStringParameters"] and event["queryStringParameters"]["vehicles"] != "RS_*;*chase":
            payload["query"]["bool"]["filter"].append(
                {
                    "match_phrase": {
                        "serial": str(event["queryStringParameters"]["vehicles"])
                    }
                }
            )
    results = es_request(payload, path, "GET")
    


    serials = { }
    for x in results['aggregations']['2']['buckets']:
        try:
            serials[x['key']] = {
                "alt": sorted(x['3']['buckets'], key=lambda k: k['key_as_string'])[-1]['1']['hits']['hits'][0]['fields']['alt'][0],
                "position": sorted(x['3']['buckets'], key=lambda k: k['key_as_string'])[-1]['5']['hits']['hits'][0]['fields']['position'][0].split(","),
                "rate": sorted(x['3']['buckets'], key=lambda k: k['key_as_string'])[-1]['4']['value']/30, # as we bucket for every 30 seconds at the moment,
                "time": sorted(x['3']['buckets'], key=lambda k: k['key_as_string'])[-1]['key_as_string']
            }
        except:
            pass

    conn = http.client.HTTPSConnection("predict.cusf.co.uk")
    serial_data={}
    for serial in serials:
        value = serials[serial]
        ascent_rate=value['rate'] if value['rate'] > 0 else 5 # this shouldn't really be used but it makes the API happy
        descent_rate=abs(value['rate'] if value['rate'] < 0 else 6) 
        burst_altitude = (value['alt']+0.05) if value['alt'] > 26000 else 26000

        conn.request("GET", 
            f"/api/v1/?launch_latitude={value['position'][0].strip()}&launch_longitude={float(value['position'][1].strip())+180}&launch_datetime={value['time']}&launch_altitude={value['alt']}&ascent_rate={ascent_rate}&burst_altitude={burst_altitude}&descent_rate={descent_rate}"
        )
        res = conn.getresponse()
        data = res.read()
        serial_data[serial] = json.loads(data.decode("utf-8"))

    output = []
    for serial in serial_data:
        value = serial_data[serial]

        
        data = []

        for stage in value['prediction']:
            if stage['stage'] == 'ascent' and serials[serial]['rate'] < 0: # ignore ascent stage if we have already burst
                continue
            else:
                for item in stage['trajectory']:
                    data.append({
                        "time": item['datetime'],
                        "lat": item['latitude'],
                        "lon": item['longitude'] -180,
                        "alt": item['altitude'],
                    })

        output.append({
            "vehicle": serial,
            "time": value['request']['launch_datetime'],
            "latitude": value['request']['launch_latitude'],
            "longitude": value['request']['launch_longitude']-180,
            "altitude": value['request']['launch_altitude'],
            "ascent_rate":value['request']['ascent_rate'],
            "descent_rate":value['request']['descent_rate'],
            "burst_altitude": value['request']['burst_altitude'],
            "landed": 0,
            "data":  json.dumps(data)
        })

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
        get_sondes_in_air_rates(
          {},{}
        )
    )


# get list of sondes,    serial, lat,lon, alt
   #           and        current rate
# for each one, request http://predict.cusf.co.uk/api/v1/?launch_latitude=-37.8136&launch_longitude=144.9631&launch_datetime=2021-02-22T00:15:18.513413Z&launch_altitude=30000&ascent_rate=5&burst_altitude=30000.1&descent_rate=5
   # have to set the burst alt slightly higher than the launch
