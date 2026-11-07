import json
import boto3
import gzip
from botocore.exceptions import ClientError
import es
from datetime import datetime, timedelta, UTC


s3 = boto3.resource('s3')

serials = {}

def process_backfill(data):
    body = ""
    for doc in data['hits']['hits']:
        if 'last_position' not in doc['_source'] and 'data' in doc['_source'] and len(doc['_source']['data']):
            doc_id = doc["_id"]
            index = doc["_index"]
            last_position = [doc['_source']['data'][-1]["lon"], doc['_source']['data'][-1]["lat"]]
            update_doc = {
                "doc": {
                    "last_position": last_position
                }
            }
            body += f'{{"update":{{"_index":"{index}","_id":"{doc_id}"}}}}' + "\n" + json.dumps(update_doc) + "\n"
    if body:
        result = es.request(body, f"_bulk", "POST")
        if 'errors' in result and result['errors'] == True:
            error_types = [x['index']['error']['type'] for x in result['items'] if 'error' in x['index']] # get all the error types
            print(result)
    else:
        print("no body to post")

def fetch_es(index=f"predictions-*"):
    payload = {
        "size": 1000,
          "query": {
                "bool": {

                    "must_not": [
                        {
                        "exists": {
                            "field": "last_position"
                        }
                        }
                    ]
                    }
                },
    }
    data = []
    indexes = []
    response = es.request(json.dumps(payload),
                           index,
                           "POST", params={"scroll": "1m",
                                          
                                           
                                           })
    try:
        process_backfill(response)
    except:
        #print(response)
        raise
    scroll_id = response['_scroll_id']
    scroll_ids = [scroll_id]
    while response['hits']['hits']:
        print("Fetching more")
        response = es.request(json.dumps({"scroll": "1m", "scroll_id": scroll_id,}), "_search/scroll", "POST")
        scroll_id = response['_scroll_id']
        scroll_ids.append(scroll_id)
        process_backfill(response)
    
    for scroll_id in scroll_ids:
        try:
            scroll_delete = es.request(json.dumps({"scroll_id": scroll_id }),
                                "_search/scroll", "DELETE")
            print(scroll_delete)
        except RuntimeError:
            pass      

    # # post data to ES bulk 

    # # dedupe indexes to clean up
    # indexes = list( dict.fromkeys(indexes) )
    # body=""
    # for key, doc in serials.items():
    #     index = "predictions-" + "-".join(doc['datetime'].split("-")[0:2]) + "-rollup"
    #     body += f'{{"index":{{"_index":"{index}"}}}}' + "\n" + json.dumps(doc) + "\n"

    # body += "\n"
    # result = es.request(body, f"_bulk", "POST")
    # if 'errors' in result and result['errors'] == True:
    #     error_types = [x['index']['error']['type'] for x in result['items'] if 'error' in x['index']] # get all the error types
    #     print(result)
    #     error_types = [a for a in error_types if a != 'mapper_parsing_exception'] # filter out mapper failures since they will never succeed
    #     if error_types:
    #         raise RuntimeError
    # for index in indexes:
    #     if "predictions-" in index: # safety check
    #         result = es.request(body, f"{index}", "DELETE")         


def find_indexes():

    response = es.request("",
                           "_cat/indices/predictions-*?format=json",
                           "GET")
    print([x['index'] for x in response])
    return [x['index'] for x in response]
    

indexes = find_indexes()
for index in indexes:
    print(f"Doing backfill {index}")
    fetch_es(index+"/_search")
    serials = {}
