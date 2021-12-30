import json
import es



def lambda_handler(event, context):
    payloads = {}
    for record in event['Records']:
        sns_message = json.loads(record["body"])
        if type(json.loads(sns_message["Message"])) == dict:
            incoming_payloads = [json.loads(sns_message["Message"])]
        else:
            incoming_payloads = json.loads(sns_message["Message"])
        for payload in incoming_payloads:
            index = payload['datetime'][:7]
            
            if index not in payloads: # create index if not exists
                payloads[index] = []
                
            payloads[index].append(payload)
        
    for index in payloads:
        body=""
        for payload in payloads[index]:
            body += "{\"index\":{}}\n" + json.dumps(payload) + "\n"
        body += "\n"

        result = es.request(body, f"telm-{index}/_doc/_bulk", "POST")
        if 'errors' in result and result['errors'] == True:
            error_types = [x['index']['error']['type'] for x in result['items'] if 'error' in x['index']] # get all the error types
            print(event)
            print(result)
            error_types = [a for a in error_types if a != 'mapper_parsing_exception'] # filter out mapper failures since they will never succeed
            if error_types:
                raise RuntimeError