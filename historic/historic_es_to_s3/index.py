import json
from botocore.awsrequest import AWSRequest
from botocore.endpoint import URLLib3Session
from botocore.auth import SigV4Auth
import boto3
import botocore.credentials
import os
import gzip
from botocore.exceptions import ClientError
from io import BytesIO

HOST = os.getenv("ES")
BUCKET = "sondehub-history"

s3 = boto3.resource('s3')

http_session = URLLib3Session()

from multiprocessing import Process

def mirror(path,params):
    session = boto3.Session()
    headers = {"Host": "search-sondes-v2-hiwdpmnjbuckpbwfhhx65mweee.us-east-1.es.amazonaws.com", "Content-Type": "application/json", "Content-Encoding":"gzip"}
    request = AWSRequest(
        method="POST", url=f"https://search-sondes-v2-hiwdpmnjbuckpbwfhhx65mweee.us-east-1.es.amazonaws.com/{path}", data=params, headers=headers
    )
    SigV4Auth(boto3.Session().get_credentials(), "es", "us-east-1").add_auth(request)
    session = URLLib3Session()
    r = session.send(request.prepare())

def es_request(payload, path, method, params=None):
    # get aws creds
    session = boto3.Session()

    compressed = BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode='w') as f:
        f.write(payload.encode('utf-8'))
    payload = compressed.getvalue()

    headers = {"Host": HOST, "Content-Type": "application/json", "Content-Encoding":"gzip"}

    request = AWSRequest(
        method=method, url=f"https://{HOST}/{path}", data=payload, headers=headers, params=params
    )
    SigV4Auth(boto3.Session().get_credentials(),
              "es", "us-east-1").add_auth(request)
    p = Process(target=mirror, args=(path,params)).start()
    r = http_session.send(request.prepare())
    return json.loads(r.text)


def fetch_es(serial):
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
    response = es_request(json.dumps(payload),
                          "telm-*/_search", "POST", params={"scroll": "1m"})
    try:
        data += [x["_source"] for x in response['hits']['hits']]
    except:
        print(response)
        raise
    scroll_id = response['_scroll_id']
    scroll_ids = [scroll_id]
    while response['hits']['hits']:
        response = es_request(json.dumps({"scroll": "1m", "scroll_id": scroll_id }),
                          "_search/scroll", "POST")
        scroll_id = response['_scroll_id']
        scroll_ids.append(scroll_id)
        data += [x["_source"] for x in response['hits']['hits']]
    for scroll_id in scroll_ids:
        scroll_delete = es_request(json.dumps({"scroll_id": scroll_id }),
                            "_search/scroll", "DELETE")
        print(scroll_delete)                
    return data

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
 
    response = es_request(json.dumps(payload),
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
    if serial in launch_sites:
        for x in data:
            x["launch_site"] = launch_sites[serial]["launch_site"]
            x["launch_site_range_estimate"] = launch_sites[serial]["launch_site_range_estimate"]
    max_alt = sorted(data, key=lambda k: int(k['alt']))[-1]
    summary = [
        data[0],
        max_alt,
        data[-1]
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

    dates = set([x['datetime'].split("T")[0].replace("-","/") for x in data])

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
    
    gz_data = gzip.compress(json.dumps(data).encode('utf-8'))
    object = s3.Object(BUCKET,f'serial/{serial}.json.gz')
    object.put(
        Body=gz_data,
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
        print(f"Getting {serial} ES")
        es = fetch_es(serial)
        print(f"Combining data {serial}")
        data = s3_data + es
        data = [dict(t) for t in {tuple(d.items()) for d in data}]
        data = sorted(data, key=lambda k: k['datetime'])  # sort by datetime
        print(f"Writing {serial} to s3")
        write_s3(serial, data, launch_sites)
        print(f"{serial} done")


if __name__ == "__main__":
    print(handler(
       {
    "Records": [
        {
            "messageId": "3b5853b3-369c-40bf-8746-130c918fbb5c",
            "receiptHandle": "AQEBg+/MIA2rSNmlrpXvk7pbi26kgIzqhairaHWGSpMgLzf2T54PLUmG+eG6CDOv35e42scDH0gppmS9RTQVu8D161oHYohhd1+0S4LtFJdgXr3At86NBIky5+y1A/wVuUm1FNQSvGKIDRgBhCgcCzLkEMNYIWWeDmg2ez2SCPu/3hmY5sc7eC32uqz5es9PspgQXOTykmoNv/q37iy2RBRDdu51Tq7yIxEr+Us3qkQrddAJ7qsA0l09aRL+/PJe1V/7MMN3CFyBATpRP/G3Gjn0Iuu4i2UhkRx2pF+0Hj8yhhHbqTMcw5sbbGIWMdsMXFQKUCHNx6HPkbuwIWo0TsINQjY7IXeZM/mNq65xC4avSlctJ/9BMzOBtFwbnRPZfHmlS5Al2nF1Vu3RecFGbTm1nQ==",
            "body": "R0230678",
            "attributes": {
                "ApproximateReceiveCount": "1",
                "SentTimestamp": "1627873604999",
                "SenderId": "AROASC7NF3EG5DNHEPSYZ:queue_data_update",
                "ApproximateFirstReceiveTimestamp": "1627873751266"
            },
            "messageAttributes": {},
            "md5OfBody": "b3d67879b6a2e7f3abd62d404e53f71f",
            "md5OfMessageAttributes": None,
            "eventSource": "aws:sqs",
            "eventSourceARN": "arn:aws:sqs:us-east-1:143841941773:update-history",
            "awsRegion": "us-east-1"
        }
    ]
}, {}))
