import json

import zlib
import base64
from datetime import datetime, timedelta
import es

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
    results = es.request(json.dumps(query), "telm-*/_search", "POST")
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
    results = es.request(json.dumps(query), "recovered*/_search", "POST")
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
                datetime(*parsedate(time_delta_header)[:7])
                - datetime.utcnow()
            ).total_seconds()
        except:
            pass

    recovered = json.loads(event["body"])

    if "datetime" not in recovered:
        recovered["datetime"] = datetime.now().isoformat()

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

    result = es.request(json.dumps(recovered), "recovered/_doc", "POST")

    # add in elasticsearch extra position field
    return {"statusCode": 200, "body": json.dumps({"message": "telm logged. Have a good day ^_^"})}


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
                    "size": 5
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
    except:
        pass

    return {"statusCode": 200, "body": json.dumps(output)}


