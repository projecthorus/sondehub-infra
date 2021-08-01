import json
from botocore.awsrequest import AWSRequest
from botocore.endpoint import URLLib3Session
from botocore.auth import SigV4Auth
import boto3
import botocore.credentials
import os
import gzip
from botocore.exceptions import ClientError

HOST = os.getenv("ES")
BUCKET = "sondehub-history"

s3 = boto3.resource('s3')

def es_request(payload, path, method, params=None):
    # get aws creds
    session = boto3.Session()

    headers = {"Host": HOST, "Content-Type": "application/json"}
    request = AWSRequest(
        method="POST", url=f"https://{HOST}/{path}", data=payload, headers=headers, params=params
    )
    SigV4Auth(boto3.Session().get_credentials(),
              "es", "us-east-1").add_auth(request)

    session = URLLib3Session()
    r = session.send(request.prepare())
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
    data += [x["_source"] for x in response['hits']['hits']]
    scroll_id = response['_scroll_id']
    while response['hits']['hits']:
        response = es_request(json.dumps({"scroll": "1m", "scroll_id": scroll_id }),
                          "_search/scroll", "POST")
        scroll_id = response['_scroll_id']
        data += [x["_source"] for x in response['hits']['hits']]
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

def write_s3(serial, data):
    #get max alt
    max_alt = sorted(data, key=lambda k: int(k['alt']))[-1]
    summary = [
        data[0],
        max_alt,
        data[-1]
    ]
    dates = set([x['datetime'].split("T")[0].replace("-","/") for x in data])
    for date in dates:
        object = s3.Object(BUCKET,f'date/{date}/{serial}.json')
        object.put(
            Body=json.dumps(summary).encode("utf-8"),
            Metadata={
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
        )
    gz_data = gzip.compress(json.dumps(data).encode('utf-8'))
    object = s3.Object(BUCKET,f'serial/{serial}.json.gz')
    object.put(
        Body=gz_data,
        ContentType='application/x-gzip',
        Metadata={
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
    )

def lambda_handler(event, context):
    payloads = {}
    for record in event['Records']:
        sns_message = json.loads(record["body"])
        serial = sns_message["Message"]
        s3_data = fetch_s3(serial)
        es = fetch_es(serial)
        data = s3_data + es
        data = [dict(t) for t in {tuple(d.items()) for d in data}]
        data = sorted(data, key=lambda k: k['datetime'])  # sort by datetime
        write_s3(serial, data)


if __name__ == "__main__":
    print(lambda_handler(
        {'Records': [{"body": "{\"Message\":\"S4520727\"}"}]}, {}))
