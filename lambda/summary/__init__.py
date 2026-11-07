import json
from datetime import datetime, timedelta, UTC
import base64
import gzip
from io import BytesIO, StringIO
import es
import dataclasses
from copy import deepcopy
import traceback
import logging

logging.basicConfig(level=logging.INFO)

MAX_LIMIT = 200

@dataclasses.dataclass
class QsFilters:
    size: int
    filters: dict

def querystring_to_filters(queryStringParameters) -> QsFilters:
    size = MAX_LIMIT
    filters =  [{"match_all": {}}]
    bool_set = {
        "should": [],
        "filter": filters
    }

    if 'limit' in queryStringParameters:
        try:
            size = int(queryStringParameters['limit'])
        except:
            raise ValueError("Could not parse limit query parameter as number")
        if size <= 0 :
            raise ValueError("Limit should be more than 0")
        if size > MAX_LIMIT:
            raise ValueError(f"Limit should be less than {MAX_LIMIT}")
        
    if (
        "lat" in queryStringParameters
        or "lon" in queryStringParameters
        or "distance" in queryStringParameters
    ):
        if not (
                "lat" in queryStringParameters
                and "lon" in queryStringParameters
                and "distance" in queryStringParameters
        ):
            raise ValueError("Geo based filter requires lat, lon and distance fields")

        try:
            bool_set["minimum_should_match"] = 1
            bool_set['should'].append(
                {
                    "geo_distance": {
                        "distance": f"{int(queryStringParameters['distance'])}m",
                        "position": {
                            "lat": float(queryStringParameters["lat"]),
                            "lon": float(queryStringParameters["lon"]),
                        },
                    }
                }
            )
        except:
            raise ValueError("Could not parse lat, lon or distance as numbers")

    if 'serial' in queryStringParameters:
        filters.append({
            "term": {
                "serial.keyword": str(queryStringParameters["serial"])
            }
        })

    if 'launchsite' in queryStringParameters:
        try:
            int(queryStringParameters['launchsite']) # just a safety check - the actual code has 0s prefixed
        except:
            raise ValueError("Error parsing launchsite, should be a number")

        filters.append({
            "term": {
                "launch_site.keyword": str(queryStringParameters["launchsite"])
            }
        })
        

    if ("from" in queryStringParameters or "to" in queryStringParameters):
        if not ("from" in queryStringParameters and "to" in queryStringParameters):
            raise ValueError("Time based queries require both from and to fields")
        try:
            from_ts = datetime.fromisoformat(queryStringParameters["from"])
            to_ts = datetime.fromisoformat(queryStringParameters["to"])
        except:
            raise ValueError("Error parsing iso format for from or to fields")

        filters.append ({
                            "range": {
                                "datetime": {
                                    "gte": from_ts.isoformat(),
                                    "lte": to_ts.isoformat(),
                                }
                            }
                        })

    
    return QsFilters(size, bool_set)


@dataclasses.dataclass
class FoundSerials:
    serials: set[str] = dataclasses.field(default_factory=list)
    hit_limit: dict[str, bool] = dataclasses.field(default_factory=dict)

def find_serials(qs_filters: QsFilters) -> FoundSerials:
    indexes = ["summary", "reverse-prediction", "predictions", "recovered", "telm"]
    msearch_body = ""
    for index in indexes:
        msearch_body += json.dumps({"index": index + "*"}) + "\n"
        
        query = {
            "timeout": "30s",
            "size": qs_filters.size,
            "stored_fields": [
                "*"
            ],
            "collapse": {"field": "serial.keyword"},
            "_source": False,
            "fields": ["serial"],
            "query": {
                "bool": deepcopy(qs_filters.filters)
            }
        }

        # last_position is only available in predictions so we need to add it as possible field here
        # copy the position query to the last_position search
        if index == "predictions" and len(query["query"]["bool"]["should"]): 
            last_position = query["query"]["bool"]["should"][0]
            last_position["geo_distance"]["last_position"] = last_position["geo_distance"]["position"] 
            del last_position["geo_distance"]["position"] 
            query["query"]["bool"]["should"].append(last_position)

        msearch_body += json.dumps(query) + "\n"

    path = f"_msearch" 
    # could save bandwidth with ?filter_path=responses.hits.hits.fields.serial%2Chits.total.relation,
    # however this will remove results from responses making it hard to link a response to a query
    response = es.request(msearch_body, path, "GET")

    serials = []
    return_serials = FoundSerials()

    for idx, index in enumerate(indexes):
        logging.info(f"{index} :  {len(response['responses'][idx]['hits']['hits'])}")
        serials += [x['fields']['serial'][0] for x in response['responses'][idx]['hits']['hits'] if ('fields' in x and 'serial' in x['fields'] and len(x['fields']['serial']) )]
        if (response['responses'][idx]['hits']['total']['relation'] == 'gte' 
            or ( len(response['responses'][idx]['hits']['hits']) >= qs_filters.size and # need to detect when we hit the limit on size due to collapsed results
                response['responses'][idx]['hits']['total']['value'] > qs_filters.size)
        ):
            return_serials.hit_limit[index] = True
        else:
            return_serials.hit_limit[index] = False

    return_serials.serials = set(serials)

    return return_serials

# for a list of serials get data from various sources
def getData(serials, size):
    queries = {
        "summary-first": ("summary", {
            "timeout": "30s",
            "size": 10000, # only care about the latest
            "collapse": {"field": "serial.keyword"},
            "_source": True,
            "sort": [{"datetime": {"order": "asc"}}],
            "query": {"terms": {"serial.keyword": list(serials)}}
        }),
        "summary-alt": ("summary", {
            "timeout": "30s",
            "size": 10000, # only care about the latest
            "collapse": {"field": "serial.keyword"},
            "_source": True,
            "sort": [{"alt": {"order": "desc"}}],
            "query": {"terms": {"serial.keyword": list(serials)}}
        }),
        "summary-last": ("summary", {
            "timeout": "30s",
            "size": 10000, # only care about the latest
            "collapse": {"field": "serial.keyword"},
            "_source": True,
            "sort": [{"datetime": {"order": "desc"}}],
            "query": {"terms": {"serial.keyword": list(serials)}}
        }),
        "recovered": ("recovered", {
            "timeout": "30s",
            "size": 10000,
            "collapse": {"field": "serial.keyword"},
            "_source": True,
            "sort": [{"datetime": {"order": "desc"}}],
            "query": {"terms": {"serial.keyword": list(serials)}}
        }),
        "reverse-prediction": ("reverse-prediction", {
            "timeout": "30s",
            "size": 10000, # Should only be one
            "collapse": {"field": "serial.keyword"},
            "_source": True,
            "sort": [{"datetime": {"order": "desc"}}],
            "query": {"terms": {"serial.keyword": list(serials)}}
        }),
        "prediction": ("prediction", {
            "timeout": "30s",
            "size": 10000, # only care about the latest
            "_source": True,
            "collapse": {"field": "serial.keyword"},
            "sort": [{"datetime": {"order": "desc"}}],
            "query": {"terms": {"serial.keyword": list(serials)}}
        }),
        "telm-first": ("telm", {
            "timeout": "30s",
            "size": 10000, # only care about the latest
            "collapse": {"field": "serial.keyword"},
            "_source": True,
            "sort": [{"datetime": {"order": "asc"}}],
            "query": {"terms": {"serial.keyword": list(serials)}}
        }),
        "telm-alt": ("telm", {
            "timeout": "30s",
            "size": 10000, # only care about the latest
            "collapse": {"field": "serial.keyword"},
            "_source": True,
            "sort": [{"alt": {"order": "desc"}}],
            "query": {"terms": {"serial.keyword": list(serials)}}
        }),
        "telm-last": ("telm", {
            "timeout": "30s",
            "size": 10000, # only care about the latest
            "collapse": {"field": "serial.keyword"},
            "_source": True,
            "sort": [{"datetime": {"order": "desc"}}],
            "query": {"terms": {"serial.keyword": list(serials)}}
        }),
    }

    msearch_body = ""
    for idx, q in queries.items():
        msearch_body += json.dumps({"index": q[0] + "*"}) + "\n"
        msearch_body += json.dumps(q[1]) + "\n"
    path = f"_msearch" 
    response = es.request(msearch_body, path, "GET")



    final_data = { serial : {
        "recovery": None,
        "predicted_landing": {
            "lat": None,
            "lon": None
        },
        "summary": [],
        "reverse_prediction": {
            "lat": None,
            "lon": None
        },
        "launchsite": None,
    } for serial in serials }

    for r in response['responses']:
        for hit in r["hits"]["hits"]:
            try:
                if (hit["_index"].startswith("summary") 
                    or hit["_index"].startswith("telm")):
                    serial = hit["_source"]['serial']
                    final_data[serial]["summary"].append(hit["_source"])

                if (hit["_index"].startswith("recovered")):
                    serial = hit["_source"]['serial']
                    final_data[serial]["recovery"] = hit["_source"]

                if (hit["_index"].startswith("prediction")):
                    serial = hit["_source"]['serial']

                    final_data[serial]["predicted_landing"]["lat"] = hit["_source"]["last_position"][1]
                    final_data[serial]["predicted_landing"]["lon"] = hit["_source"]["last_position"][0]
                if (hit["_index"].startswith("reverse-prediction")):
                    serial = hit["_source"]['serial']
                    if "data" in hit["_source"] and len(hit["_source"]['data']) > 0:
                        last_pred = hit["_source"]['data'][-1]
                        final_data[serial]["reverse_prediction"]["lat"] = last_pred["lat"]
                        final_data[serial]["reverse_prediction"]["lon"] = last_pred["lon"]
                        if 'launch_site' in hit["_source"]:
                            final_data[serial]["launchsite"] = hit["_source"]['launch_site']
            except:
                logging.info("Error parse opensearch doc into final_data")
                traceback.print_exc()
                logging.info(hit)

    # dedup summary frames
    for serial in serials:
        final_data[serial]["summary"] = [dict(t) for t in {tuple(d.items()) for d in final_data[serial]["summary"]}]

    # only keep the first, last and highest alt
    for serial in serials:
            by_date = sorted(final_data[serial]["summary"], key=lambda d: d['datetime'])
            alt = sorted(final_data[serial]["summary"], key=lambda d: d['alt'])[-1]
            final_data[serial]["summary"] = [
                by_date[0],
                alt,
                by_date[-1]
            ]

    return final_data

def get(event, context):
    # 1. parse / validate query strings
    # 2. get list of serials that match from the various indexes
    # 3. then requery the indexes based on serial number with no other filters

    if 'queryStringParameters' in event:
        try:
            qs_filters = querystring_to_filters(event['queryStringParameters'])
        except ValueError as e:
            return {
                "body": f"{str(e)}",
                "statusCode": 400
            }
    else:
        qs_filters = querystring_to_filters({}) # empty filters / size only

    logging.info(qs_filters)

    # handle when the combined list of serials is to large
    found_serials = find_serials(qs_filters)
    if len(found_serials.serials) > qs_filters.size: # we might want to remove this as the max terms limit is 65,536 so we could possibly get away with it.
        found_serials.serials = set(list(found_serials.serials)[:qs_filters.size])
        found_serials.hit_limit["total"] = True
    else:
        found_serials.hit_limit["total"] = False

    logging.info(found_serials)

    data = getData(found_serials.serials, qs_filters.size)

    return_obj = {
        "_metadata": {
                    "limits": found_serials.hit_limit
        },
        "radiosondes": data,
    }

    compressed = BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode='w') as f:
        json_response = json.dumps(return_obj)
        f.write(json_response.encode('utf-8'))
    
    gzippedResponse = compressed.getvalue()
    return {
            "body": base64.b64encode(gzippedResponse).decode(),
            "isBase64Encoded": True,
            "statusCode": 200,
            "headers": {
                "Content-Encoding": "gzip",
                "content-type": "application/json"
            }
        }
