import zlib
import boto3
import gzip
from botocore.awsrequest import AWSRequest
from botocore.endpoint import URLLib3Session
from botocore.auth import SigV4Auth
from io import BytesIO
import json
import os
import zlib

es_session = URLLib3Session()
ES_HOST = os.getenv("ES")

def request(payload, path, method, params=None):

    compressed = BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode='w') as f:
        f.write(payload.encode('utf-8'))
    payload = compressed.getvalue()

    headers = {"Host": ES_HOST, "Content-Type": "application/json",
               "Content-Encoding": "gzip", 'Accept-Encoding': 'gzip'}

    request = AWSRequest(
        method=method, url=f"https://{ES_HOST}/{path}", data=payload, headers=headers, params=params
    )
    SigV4Auth(boto3.Session().get_credentials(),
              "es", "us-east-1").add_auth(request)
    
    r = es_session.send(request.prepare())

    if r.status_code != 200 and r.status_code != 201:
        print(zlib.decompress(r.content, 16 + zlib.MAX_WBITS))
        raise RuntimeError
    
    if (
       'Content-Encoding' in r.headers
        and r.headers['Content-Encoding'] == 'gzip'
    ):
        return json.loads(zlib.decompress(r.content, 16 + zlib.MAX_WBITS))
    else:
        return json.loads(r.text)
