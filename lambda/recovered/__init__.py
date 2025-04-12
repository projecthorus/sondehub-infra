import json

import zlib
import base64
from datetime import datetime, timedelta
import es
import boto3
import botocore.exceptions
import time
from email.utils import parsedate

import sys
sys.path.append("sns_to_mqtt/vendor")

import config_handler
import random

def sondeExists(serial):
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
                        "term": {
                            "serial.keyword": serial
                        }
                    }
                ]
            }
        }
    }
    results = es.request(json.dumps(query), "telm-*/_search", "POST")
    if len(results["aggregations"]["1"]["hits"]["hits"]) > 0:
        return True
    
    # if there's a historic file created for this sonde, use that instead
    try:
        s3 = boto3.resource('s3')
        object = s3.Object('sondehub-history', f'serial/{serial}.json.gz')
        
        object.load()
        return True
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            return False
        else:
            # Something else has gone wrong.
            raise


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
                        "term": {
                            "serial.keyword": serial
                        }
                    },
                    {
                        "term": {
                            "recovered.keyword": True # not sure if this right? should be a bool time. function is never called though
                        }
                    },
                ]
            }
        }
    }
    results = es.request(json.dumps(query), "recovered*/_search", "POST")
    return results["aggregations"]["1"]["hits"]["hits"]

client = None


connected_flag = False
setup = False

import socket
socket.setdefaulttimeout(1)


## MQTT functions
def connect():
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish
    #client.tls_set()
    client.username_pw_set(config_handler.get("MQTT","USERNAME"), password=config_handler.get("MQTT","PASSWORD"))
    HOSTS = config_handler.get("MQTT","HOST").split(",")
    PORT = int(config_handler.get("MQTT","PORT", default="8080"))
    if PORT == 443:
        client.tls_set()
    HOST = random.choice(HOSTS)
    print(f"Connecting to {HOST}")
    client.connect(HOST, PORT, 5)
    client.loop_start()
    print("loop started")

def on_disconnect(client, userdata, rc):
    global connected_flag
    print("disconnected")
    connected_flag=False #set flag

def on_connect(client, userdata, flags, rc):
    global connected_flag
    if rc==0:
        print("connected")
        connected_flag=True #set flag
    else:
        print("Bad connection Returned code")

def on_publish(client, userdata, mid):
    pass

def put(event, context):
    global client, setup
    import paho.mqtt.client as mqtt

    # Setup MQTT
    if not client:
        client = mqtt.Client(transport="websockets")

    # Connect to MQTT
    if not setup:
        connect()
        setup = True

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
                datetime(*parsedate(time_delta_header)[:7])
                - datetime.utcnow()
            ).total_seconds()
        except:
            pass

    recovered = json.loads(event["body"])

    if "datetime" not in recovered:
        recovered["datetime"] = datetime.now().isoformat()

    if recovered["serial"] == "":
        return {"statusCode": 400, "body":  json.dumps({"message": "serial cannot be empty"})}

    if not sondeExists(recovered["serial"]):
        return {"statusCode": 400, "body":  json.dumps({"message": "serial not found in db"})}

    recovered['position'] = [float(recovered['lon']), float(recovered['lat'])]
    
    while not connected_flag:
        time.sleep(0.01) # wait until connected

    client.publish(
        topic=f'recovery/{recovered["serial"]}',
        payload=json.dumps(recovered),
        qos=0,
        retain=False
    )

    result = es.request(json.dumps(recovered), "recovered/_doc", "POST")


    time.sleep(0.3) # give paho mqtt 300ms to send messages this could be improved on but paho mqtt is a pain to interface with

    # add in elasticsearch extra position field
    return {"statusCode": 200, "body": json.dumps({"message": "Recovery logged. Have a good day ^_^"})}


def get(event, context):
    filters = []
    should = []
    last = 259200
    serials = None
    lat = None
    lon = None
    distance = None

    # grab query parameters
    if "queryStringParameters" in event:
        if "last" in event["queryStringParameters"]:
            last = int(event['queryStringParameters']['last'])
        if "serial" in event["queryStringParameters"]:
            serials = event['queryStringParameters']['serial'].split(",")
        if "last" not in event["queryStringParameters"] and "serial" in event["queryStringParameters"]:
            last = 0
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
    if serials:
        for serial in serials:
            should.append(
                {
                    "term": {
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
                "filter": filters,
                "should": should,
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
    if serials:
        query["query"]["bool"]["minimum_should_match"] = 1
    results = es.request(json.dumps(query), "recovered*/_search", "POST")
    output = [x['1']['hits']['hits'][0]["_source"]
              for x in results['aggregations']['2']['buckets']]
    return {"statusCode": 200, "body": json.dumps(output)}


def stats(event, context):
    filters = []
    should = []
    duration = 0
    serials = None
    lat = None
    lon = None
    distance = None
    requested_time = None

    # grab query parameters
    if "queryStringParameters" in event:
        if "duration" in event["queryStringParameters"]:
            duration = int(event['queryStringParameters']['duration'])
        if "lat" in event["queryStringParameters"]:
            lat = float(event["queryStringParameters"]['lat'])
        if "lon" in event["queryStringParameters"]:
            lon = float(event["queryStringParameters"]['lon'])
        if "distance" in event["queryStringParameters"]:
            distance = int(event["queryStringParameters"]['distance'])
        if "datetime" in event["queryStringParameters"]:
            requested_time = datetime.fromisoformat(
                event["queryStringParameters"]["datetime"].replace("Z", "+00:00")
            )
    if duration != 0:
        if requested_time:
            lt = requested_time + timedelta(0, 1)
            gte = requested_time - timedelta(0, duration)           
            filters.append(
                {
                    "range": {
                        "datetime": {"gte": gte.isoformat(), "lt": lt.isoformat()}
                    }
                }
            )
        else:
            lt = datetime.now() + timedelta(0, 1)
            gte = datetime.now() - timedelta(0, duration)           
            filters.append(
                {
                    "range": {
                        "datetime": {"gte": gte.isoformat(), "lt": lt.isoformat()}
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
                "filter": filters,
                "should": should,
            }
        },
        "aggs": {
            "chaser_count": {
                "cardinality": {
                    "field": "recovered_by.keyword"
                }
            },  
            "breakdown": {
                "terms": {
                    "field": "recovered",
                    "order": {
                        "counts": "desc"
                    },
                    "size": 5
                },
                "aggs": {
                    "counts": {
                        "cardinality": {
                            "field": "serial.keyword"
                        }
                    }
                }
            },
            "top_recovered": {
                "terms": {
                    "field": "recovered_by.keyword",
                    "order": {
                        "recovered_by": "desc"
                    },
                    "size": 6
                },
                "aggs": {
                    "recovered_by": {
                        "cardinality": {
                            "field": "serial.keyword"
                        }
                    }
                }
            },
            "total_count": {
                "cardinality": {
                    "field": "serial.keyword"
                }
            }
        }
    }
    results = es.request(json.dumps(query), "recovered*/_search", "POST")

    output = {
        "total": 0,
        "recovered": 0,
        "failed": 0,
        "chaser_count": 0,
        "top_chasers": {}
    }
    try:
        output['total'] = results['aggregations']['total_count']['value']
    except:
        output['total'] = 0
    stats = { x['key_as_string'] : x['counts']['value'] for x in results['aggregations']['breakdown']['buckets']}
    try:
        output['recovered'] = stats['true']
    except:
        pass

    try:
        output['failed'] = stats['false']
    except:
        pass    

    try:
        output['chaser_count'] = results['aggregations']['chaser_count']['value']
    except:
        output['chaser_count'] = 0

    try:
        output['top_chasers'] = { x['key'] : x['recovered_by']['value'] for x in results['aggregations']['top_recovered']['buckets']}
        if "" in output['top_chasers']:
            del output['top_chasers'][""]
    except:
        pass

    return {"statusCode": 200, "body": json.dumps(output)}


