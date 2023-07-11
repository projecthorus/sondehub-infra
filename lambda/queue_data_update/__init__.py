import json
import boto3
import os
import es


HOST = os.getenv("ES")

sqs = boto3.client('sqs', region_name="us-east-1")

def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]


def handler(event, context):
    query = {
        "aggs": {
            "serials": {
                "terms": {
                    "field": "serial.keyword",
                    "size": 10000
                }
            }
        },
        "size": 0,
        "_source": {
            "excludes": []
        },
        "query": {
            "bool": {
                "must_not": [{"term": {"serial": "xxxxxxxx"}}],
                "filter": [
                    {
                        "range": {
                            "datetime": {
                                "gte": "now-24h",
                                "format": "strict_date_optional_time"
                            }
                        }
                    }
                ]
            }
        }
    }

    results = es.request(json.dumps(query), "telm-*/_search", "POST")
    serials = [ x['key'] for x in results['aggregations']['serials']['buckets'] ]
    for serial_batch in batch(serials, 10):
        sqs.send_message_batch(
            QueueUrl="https://sqs.us-east-1.amazonaws.com/143841941773/update-history",
            Entries=[
                {
                    "Id": str(serial_batch.index(x)),
                    "MessageBody": x
                }
            for x in serial_batch]
        )
    return [ x['key'] for x in results['aggregations']['serials']['buckets'] ]
    #TODO add to SQS queue



# this script will find list of sondes seen in the last 48 hours and add them to the queue to be updated (including the first and last date they were seen)
