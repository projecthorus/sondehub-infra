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
import http.client
import math
import logging

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.DEBUG)

HOST = os.getenv("ES")

def getDensity(altitude):
    """ 
	Calculate the atmospheric density for a given altitude in metres.
	This is a direct port of the oziplotter Atmosphere class
	"""

    # Constants
    airMolWeight = 28.9644  # Molecular weight of air
    densitySL = 1.225  # Density at sea level [kg/m3]
    pressureSL = 101325  # Pressure at sea level [Pa]
    temperatureSL = 288.15  # Temperature at sea level [deg K]
    gamma = 1.4
    gravity = 9.80665  # Acceleration of gravity [m/s2]
    tempGrad = -0.0065  # Temperature gradient [deg K/m]
    RGas = 8.31432  # Gas constant [kg/Mol/K]
    R = 287.053
    deltaTemperature = 0.0

    # Lookup Tables
    altitudes = [0, 11000, 20000, 32000, 47000, 51000, 71000, 84852]
    pressureRels = [
        1,
        2.23361105092158e-1,
        5.403295010784876e-2,
        8.566678359291667e-3,
        1.0945601337771144e-3,
        6.606353132858367e-4,
        3.904683373343926e-5,
        3.6850095235747942e-6,
    ]
    temperatures = [288.15, 216.65, 216.65, 228.65, 270.65, 270.65, 214.65, 186.946]
    tempGrads = [-6.5, 0, 1, 2.8, 0, -2.8, -2, 0]
    gMR = gravity * airMolWeight / RGas

    # Pick a region to work in
    i = 0
    if altitude > 0:
        while altitude > altitudes[i + 1]:
            i = i + 1

    # Lookup based on region
    baseTemp = temperatures[i]
    tempGrad = tempGrads[i] / 1000.0
    pressureRelBase = pressureRels[i]
    deltaAltitude = altitude - altitudes[i]
    temperature = baseTemp + tempGrad * deltaAltitude

    # Calculate relative pressure
    if math.fabs(tempGrad) < 1e-10:
        pressureRel = pressureRelBase * math.exp(
            -1 * gMR * deltaAltitude / 1000.0 / baseTemp
        )
    else:
        pressureRel = pressureRelBase * math.pow(
            baseTemp / temperature, gMR / tempGrad / 1000.0
        )

    # Add temperature offset
    temperature = temperature + deltaTemperature

    # Finally, work out the density...
    speedOfSound = math.sqrt(gamma * R * temperature)
    pressure = pressureRel * pressureSL
    density = densitySL * pressureRel * temperatureSL / temperature

    return density


def seaLevelDescentRate(descent_rate, altitude):
    """ Calculate the descent rate at sea level, for a given descent rate at altitude """

    rho = getDensity(altitude)
    return math.sqrt((rho / 1.225) * math.pow(descent_rate, 2))


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
                            "fixed_interval": "5s"
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
                                "buckets_path": "4-metric",
                                "gap_policy": "skip",
                                "lag": 5
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
                                    "gte": "now-5m",
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
                            "software_name": "SondehubV1"
                        }
                    }
                ]
                    }
                }
            }
    if "queryStringParameters" in event:
        if "vehicles" in event["queryStringParameters"] and event["queryStringParameters"]["vehicles"] != "RS_*;*chase"  and event["queryStringParameters"]["vehicles"] != "":
            payload["query"]["bool"]["filter"].append(
                {
                    "match_phrase": {
                        "serial": str(event["queryStringParameters"]["vehicles"])
                    }
                }
            )
    logging.debug("Start ES Request")
    results = es_request(payload, path, "GET")
    logging.debug("Finished ES Request")
    


    serials = { }
    for x in results['aggregations']['2']['buckets']:
        try:
            serials[x['key']] = {
                "alt": sorted(x['3']['buckets'], key=lambda k: k['key_as_string'])[-1]['1']['hits']['hits'][0]['fields']['alt'][0],
                "position": sorted(x['3']['buckets'], key=lambda k: k['key_as_string'])[-1]['5']['hits']['hits'][0]['fields']['position'][0].split(","),
                "rate": sorted(x['3']['buckets'], key=lambda k: k['key_as_string'])[-1]['4']['value']/25, # as we bucket for every 5 seconds with a lag of 5
                "time": sorted(x['3']['buckets'], key=lambda k: k['key_as_string'])[-1]['key_as_string']
            }
        except:
            pass

    conn = http.client.HTTPSConnection("predict.cusf.co.uk")
    serial_data={}
    logging.debug("Start Predict")
    for serial in serials:

        value = serials[serial]
        ascent_rate=value['rate'] if value['rate'] > 0.5 else 5 # this shouldn't really be used but it makes the API happy
        descent_rate= seaLevelDescentRate(abs(value['rate']),value['alt']) if value['rate'] < 0 else 6
        if descent_rate < 0.5:
            continue
        if value['rate'] < 0:
            burst_altitude = value['alt']+0.05
        else:
            burst_altitude = (value['alt']+0.05) if value['alt'] > 26000 else 26000

        longitude = float(value['position'][1].strip())
        if longitude < 0:
            longitude += 360
        url = f"/api/v1/?launch_latitude={value['position'][0].strip()}&launch_longitude={longitude:.2f}&launch_datetime={value['time']}&launch_altitude={value['alt']:.2f}&ascent_rate={ascent_rate:.2f}&burst_altitude={burst_altitude:.2f}&descent_rate={descent_rate:.2f}"
        

        conn.request("GET", url
            
        )
        res = conn.getresponse()
        data = res.read()
        serial_data[serial] = json.loads(data.decode("utf-8"))
    logging.debug("Stop Predict")
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
                        "time": int(datetime.fromisoformat(item['datetime'].split(".")[0].replace("Z","")).timestamp()),
                        "lat": item['latitude'],
                        "lon": item['longitude'] - 360 if item['longitude'] > 180 else item['longitude'],
                        "alt": item['altitude'],
                    })

        output.append({
            "vehicle": serial,
            "time": value['request']['launch_datetime'],
            "latitude": value['request']['launch_latitude'],
            "longitude": value['request']['launch_longitude'],
            "altitude": value['request']['launch_altitude'],
            "ascent_rate":value['request']['ascent_rate'],
            "descent_rate":value['request']['descent_rate'],
            "burst_altitude": value['request']['burst_altitude'],
            "landed": 0,
            "data":  json.dumps(data)
        })
    logging.debug("Finished")
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
    predict(
          {"queryStringParameters" : {
}},{}
        )
    


# get list of sondes,    serial, lat,lon, alt
   #           and        current rate
# for each one, request http://predict.cusf.co.uk/api/v1/?launch_latitude=-37.8136&launch_longitude=144.9631&launch_datetime=2021-02-22T00:15:18.513413Z&launch_altitude=30000&ascent_rate=5&burst_altitude=30000.1&descent_rate=5
   # have to set the burst alt slightly higher than the launch
