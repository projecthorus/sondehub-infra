import boto3
import json
import re

MATCH_OBJECT = re.compile(r"^gfs.\d{8}/\d{2}/atmos/gfs.t\d{2}z.pgrb2.0p50.f192$")
BUCKET = 'noaa-gfs-bdp-pds'
SERVICE_NAME="tawhiri"
CLUSTER_NAME="Tawhiri"
ecs = boto3.client('ecs', region_name="us-east-1")

def handler(event, context):
    for record in event["Records"]:
        message = json.loads(record["Sns"]["Message"])
        for inner_record in message['Records']:
            if "ObjectCreated" in inner_record['eventName']:
                if inner_record['s3']['bucket']['name'] == BUCKET:
                    print(inner_record['s3']['object']['key'])
                    if MATCH_OBJECT.match(inner_record['s3']['object']['key']):
                        print(f"Found new GFS - updating service {inner_record['s3']['object']['key']}")
                        ecs.update_service(cluster=CLUSTER_NAME, service=SERVICE_NAME, forceNewDeployment=True)

