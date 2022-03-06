import json
import boto3
import gzip
from botocore.exceptions import ClientError
import es

BUCKET = "sondehub-history"

s3 = boto3.resource('s3')

def fetch_es(serial, s3_data):
    payload = {
        "size": 10000,
        "sort": [
            {
                "datetime": {
                    "order": "desc",
                    "unmapped_type": "boolean"
                }
            }
        ],

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
    data = []
    response = es.request(json.dumps(payload),
                          "telm-*/_search", "POST", params={"scroll": "1m"})
    try:
        add_unique(s3_data,[x["_source"] for x in response['hits']['hits']])
    except:
        print(response)
        raise
    scroll_id = response['_scroll_id']
    scroll_ids = [scroll_id]
    while response['hits']['hits']:
        response = es.request(json.dumps({"scroll": "1m", "scroll_id": scroll_id }),
                          "_search/scroll", "POST")
        scroll_id = response['_scroll_id']
        scroll_ids.append(scroll_id)
        add_unique(s3_data,[x["_source"] for x in response['hits']['hits']])
    for scroll_id in scroll_ids:
        try:
            scroll_delete = es.request(json.dumps({"scroll_id": scroll_id }),
                                "_search/scroll", "DELETE")
            print(scroll_delete)
        except RuntimeError:
            pass                

def add_unique(s3_data, es_r):
    for row in es_r:
        s3_data.add(json.dumps(row, sort_keys=True))

def fetch_s3(serial):
    try:
        object = s3.Object(BUCKET,f'serial/{serial}.json.gz')
        with gzip.GzipFile(fileobj=object.get()["Body"]) as gzipfile:
            return json.loads(gzipfile.read().decode("utf-8"))
    except ClientError as ex:
        if ex.response['Error']['Code'] == 'NoSuchKey':
            return []
        else:
            raise

def fetch_launch_sites():
    payload = {
        "aggs": {
            "2": {
            "terms": {
                "field": "serial.keyword",
                "order": {
                "_key": "desc"
                },
                "size": 10000
            },
            "aggs": {
                "1": {
                "top_hits": {
                    "docvalue_fields": [
                    {
                        "field": "launch_site.keyword"
                    }
                    ],
                    "_source": "launch_site.keyword",
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
                "3": {
                "top_hits": {
                    "docvalue_fields": [
                    {
                        "field": "launch_site_range_estimate"
                    }
                    ],
                    "_source": "launch_site_range_estimate",
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
        },
        "size": 0,
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
                        "gte": "now-24h",
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
 
    response = es.request(json.dumps(payload),
                          "reverse-prediction-*/_search", "POST")
    data = { x['key'] : x for x in response['aggregations']['2']['buckets']}
    output = {}
    for serial in data:
        try:
            output[serial] = {
                "launch_site": data[serial]['1']['hits']['hits'][0]['fields']['launch_site.keyword'][0],
                "launch_site_range_estimate": data[serial]['3']['hits']['hits'][0]['fields']['launch_site_range_estimate'][0]
            }
        except:
            continue
    return output

def write_s3(serial, data, launch_sites):
    #get max alt
    append_data = ""
    if serial in launch_sites:
        append_data = f"\"launch_site\": \"{launch_sites[serial]['launch_site']}\", \"launch_site_range_estimate\": {launch_sites[serial]['launch_site_range_estimate']}"
    max_alt = sorted(data, key=lambda k: json.loads(k)['alt'])[-1]
    summary = [
        json.loads(data[0]),
        json.loads(max_alt),
        json.loads(data[-1])
    ]
    metadata = {
                "first-lat": str(summary[0]['lat']),
                "first-lon": str(summary[0]['lon']),
                "first-alt": str(summary[0]['alt']),
                "max-lat": str(summary[1]['lat']),
                "max-lon": str(summary[1]['lon']),
                "max-alt": str(summary[1]['alt']),
                "last-lat": str(summary[2]['lat']),
                "last-lon": str(summary[2]['lon']),
                "last-alt": str(summary[2]['alt'])
            }
    if serial in launch_sites:
        metadata["launch_site"] = launch_sites[serial]["launch_site"]

    dates = set([json.loads(x)['datetime'].split("T")[0].replace("-","/") for x in data])

    for date in dates:
        object = s3.Object(BUCKET,f'date/{date}/{serial}.json')
        object.put(
            Body=json.dumps(summary).encode("utf-8"),
            Metadata=metadata
        )
    
    if serial in launch_sites:
        object = s3.Object(BUCKET,f'launchsites/{launch_sites[serial]["launch_site"]}/{date}/{serial}.json')
        object.put(
            Body=json.dumps(summary).encode("utf-8"),
            Metadata=metadata
        )
    output = "["
    if append_data:
        data = [ x[:-1] + ", " + append_data + "}" for x in data ]
    output += ",".join(data)
    output += "]"
    data = gzip.compress(output.encode('utf-8'))
    object = s3.Object(BUCKET,f'serial/{serial}.json.gz')
    object.put(
        Body=data,
        ContentType='application/json',
        ContentEncoding='gzip',
        Metadata=metadata
    )


def handler(event, context):
    print(json.dumps(event))
    payloads = {}
    launch_sites = fetch_launch_sites()
    for record in event['Records']:
        serial = record["body"]
        print(f"Getting {serial} S3")
        s3_data = fetch_s3(serial)
        s3_data = {json.dumps(x, sort_keys=True) for x in s3_data} # convert to a set
        print(f"Getting {serial} ES")
        es = fetch_es(serial, s3_data)
        #print("Back to list")
        #s3_data = [json.loads(x) for x in s3_data]
        print("Sorting")
        s3_data=list(s3_data)
        s3_data.sort(key=lambda k: json.loads(k)['datetime'])
        print(f"Writing {serial} to s3")
        write_s3(serial, s3_data, launch_sites)
        print(f"{serial} done")

