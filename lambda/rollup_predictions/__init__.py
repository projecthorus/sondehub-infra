import json
import boto3
import gzip
from botocore.exceptions import ClientError
import es
from datetime import datetime, timedelta


s3 = boto3.resource('s3')

serials = {}

def fetch_es(index=f"predictions-*,-predictions-{datetime.now().strftime('%Y-%m')},-predictions-{(datetime.now() - timedelta(days=27)).strftime('%Y-%m')},-predictions-*-rollup/_search"):
    payload = {
        "size": 1000
    }
    data = []
    indexes = []
    response = es.request(json.dumps(payload),
                           index,
                           "POST", params={"scroll": "1m"})
    try:
        add_unique([x["_source"] for x in response['hits']['hits']])
    except:
        print(response)
        raise
    scroll_id = response['_scroll_id']
    scroll_ids = [scroll_id]
    while response['hits']['hits']:
        print("Fetching more")
        response = es.request(json.dumps({"scroll": "1m", "scroll_id": scroll_id }),
                          "_search/scroll", "POST")
        scroll_id = response['_scroll_id']
        scroll_ids.append(scroll_id)
        add_unique([x["_source"] for x in response['hits']['hits']])
        indexes += [x["_index"] for x in response['hits']['hits']]
    for scroll_id in scroll_ids:
        try:
            scroll_delete = es.request(json.dumps({"scroll_id": scroll_id }),
                                "_search/scroll", "DELETE")
            print(scroll_delete)
        except RuntimeError:
            pass      

    # post data to ES bulk 

    # dedupe indexes to clean up
    indexes = list( dict.fromkeys(indexes) )
    body=""
    for key, doc in serials.items():
        index = "predictions-" + "-".join(doc['datetime'].split("-")[0:2]) + "-rollup"
        body += f'{{"index":{{"_index":"{index}"}}}}' + "\n" + json.dumps(doc) + "\n"

    body += "\n"
    result = es.request(body, f"_bulk", "POST")
    if 'errors' in result and result['errors'] == True:
        error_types = [x['index']['error']['type'] for x in result['items'] if 'error' in x['index']] # get all the error types
        print(result)
        error_types = [a for a in error_types if a != 'mapper_parsing_exception'] # filter out mapper failures since they will never succeed
        if error_types:
            raise RuntimeError
    for index in indexes:
        if "predictions-" in index: # safety check
            result = es.request(body, f"{index}", "DELETE")         

def add_unique(es_r):
    for row in es_r:
        serial = row['serial']
        if serial not in serials or datetime.fromisoformat(serials[serial]['datetime'].replace("Z", "+00:00")) < datetime.fromisoformat(row['datetime'].replace("Z", "+00:00")):
            serials[serial] = row
    print(f"Number of serials: {len(serials)}")

def handler(event, context):
    print(json.dumps(event))
    fetch_es()