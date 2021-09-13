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
import math
import logging
import gzip
from io import BytesIO

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
                                "_source": {"includes": ["position", "type", "subtype"]},
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
                                    "gte": "now-10m",
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
                },
                "size": 0
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
            payload['query']['bool']['filter'][1]['range']['datetime']['gte'] = 'now-6h' # for single sonde allow longer predictions
    logging.debug("Start ES Request")
    results = es_request(json.dumps(payload), path, "GET")
    logging.debug("Finished ES Request")
    


    serials = { }
    for x in results['aggregations']['2']['buckets']:
        try:
            serials[x['key']] = {
                "alt": sorted(x['3']['buckets'], key=lambda k: k['key_as_string'])[-1]['1']['hits']['hits'][0]['fields']['alt'][0],
                "position": sorted(x['3']['buckets'], key=lambda k: k['key_as_string'])[-1]['5']['hits']['hits'][0]['fields']['position'][0].split(","),
                "rate": sorted(x['3']['buckets'], key=lambda k: k['key_as_string'])[-1]['4']['value']/25, # as we bucket for every 5 seconds with a lag of 5
                "time": sorted(x['3']['buckets'], key=lambda k: k['key_as_string'])[-1]['key_as_string'],
                "type": sorted(x['3']['buckets'], key=lambda k: k['key_as_string'])[-1]['5']['hits']['hits'][0]["_source"]["type"],
                "subtype": sorted(x['3']['buckets'], key=lambda k: k['key_as_string'])[-1]['5']['hits']['hits'][0]["_source"]["subtype"]
            }
        except:
            pass

    conn = http.client.HTTPSConnection("tawhiri.v2.sondehub.org")
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
        url = f"/api/v1/?launch_latitude={value['position'][0].strip()}&launch_longitude={longitude}&launch_datetime={value['time']}&launch_altitude={value['alt']:.2f}&ascent_rate={ascent_rate:.2f}&burst_altitude={burst_altitude:.2f}&descent_rate={descent_rate:.2f}"
        

        conn.request("GET", url
            
        )
        res = conn.getresponse()
        data = res.read()
        if res.code != 200:
            logging.debug(data)
        serial_data[serial] = json.loads(data.decode("utf-8"))
    logging.debug("Stop Predict")
    output = []
    for serial in serial_data:
        value = serial_data[serial]

        
        data = []
        if 'prediction' in value:
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
            output.append(
                {
                    "serial": serial,
                    "type": serials[serial]['type'],
                    "subtype": serials[serial]['subtype'],
                    "datetime": value['request']['launch_datetime'],
                    "position": [
                            value['request']['launch_longitude'] - 360 if value['request']['launch_longitude'] > 180 else value['request']['launch_longitude'],
                            value['request']['launch_latitude']
                        ],
                    "altitude": value['request']['launch_altitude'],
                    "ascent_rate": value['request']['ascent_rate'],
                    "descent_rate": value['request']['descent_rate'],
                    "burst_altitude": value['request']['burst_altitude'],
                    "descending": True if serials[serial]['rate'] < 0 else False,
                    "landed": False, # I don't think this gets used anywhere?
                    "data": data
                }
            )

    # ES bulk update
    body=""
    for payload in output:
        body += "{\"index\":{}}\n" + json.dumps(payload) + "\n"
    body += "\n"
    index = datetime.now().strftime("%Y-%m")
    result = es_request(body, f"predictions-{index}/_doc/_bulk", "POST")
    if 'errors' in result and result['errors'] == True:
        error_types = [x['index']['error']['type'] for x in result['items'] if 'error' in x['index']] # get all the error types
        error_types = [a for a in error_types if a != 'mapper_parsing_exception'] # filter out mapper failures since they will never succeed
        if error_types:
            print(event)
            print(result)
            raise RuntimeError
    
    logging.debug("Finished")
    return

def es_request(params, path, method):
    # get aws creds
    session = boto3.Session()
    
    compressed = BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode='w') as f:
        f.write(params.encode('utf-8'))
    params = compressed.getvalue()


    headers = {"Host": HOST, "Content-Type": "application/json", "Content-Encoding":"gzip"}
    request = AWSRequest(
        method=method, url=f"https://{HOST}/{path}", data=params, headers=headers
    )
    SigV4Auth(boto3.Session().get_credentials(), "es", "us-east-1").add_auth(request)

    session = URLLib3Session()
    r = session.send(request.prepare())

    if r.status_code != 200:
        raise RuntimeError
    return json.loads(r.text)


if __name__ == "__main__":
    print(predict(
          {},{}
        ))
    

