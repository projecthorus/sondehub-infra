import boto3
import json
import re

MATCH_OBJECT = re.compile(r"^gfs.\d{8}/\d{2}/atmos/gfs.t\d{2}z.prgb2.0p50.f192$")
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
                    if MATCH_OBJECT.match(inner_record['s3']['object']['key']):
                        print(f"Found new GFS - updating service {inner_record['s3']['object']['key']}")
                        ecs.update_service(cluster=CLUSTER_NAME, service=SERVICE_NAME, forceNewDeployment=True)

if __name__ == "__main__":
    handler(
    {
    "Records": [
        {
            "EventSource": "aws:sns",
            "EventVersion": "1.0",
            "EventSubscriptionArn": "arn:aws:sns:us-east-1:123901341784:NewGFSObject:47c29dbe-6482-4495-bc25-41686b9c8f30",
            "Sns": {
                "Type": "Notification",
                "MessageId": "4ddb4adc-c245-5f45-bb5b-10c24be3e4b5",
                "TopicArn": "arn:aws:sns:us-east-1:123901341784:NewGFSObject",
                "Subject": "Amazon S3 Notification",
                "Message": "{\"Records\":[{\"eventVersion\":\"2.1\",\"eventSource\":\"aws:s3\",\"awsRegion\":\"us-east-1\",\"eventTime\":\"2021-11-29T07:55:17.516Z\",\"eventName\":\"ObjectCreated:Put\",\"userIdentity\":{\"principalId\":\"AWS:AROAIFS7SMW4FSODZYIMM:Fetch_GFS_NCEP\"},\"requestParameters\":{\"sourceIPAddress\":\"52.204.74.204\"},\"responseElements\":{\"x-amz-request-id\":\"ZSHQPQ51RFMMDSCJ\",\"x-amz-id-2\":\"NSLglU4PxYEEXmKN4LHrJg3jeHjKafCU6SaDSWbfwKjvcfKsrpMB/SLvfW+lKjn0d256kNhV845Cu/OHxMrC/GQ1EEVn4ODC\"},\"s3\":{\"s3SchemaVersion\":\"1.0\",\"configurationId\":\"NjNmNjg3MWUtNTAzNy00YTcxLWI3ZGMtM2MzMjI2OGY5Y2Ey\",\"bucket\":{\"name\":\"noaa-gfs-bdp-pds\",\"ownerIdentity\":{\"principalId\":\"A2AJV00K47QOI1\"},\"arn\":\"arn:aws:s3:::noaa-gfs-bdp-pds\"},\"object\":{\"key\":\"gfs.20211127/12/atmos/gfs.t12z.prgb2.0p50.f192\",\"size\":5242,\"eTag\":\"2e6fa824124d06b1e0af0a6c852f37cc\",\"sequencer\":\"0061A48765785BC5E7\"}}}]}",
                "Timestamp": "2021-11-29T07:55:18.716Z",
                "SignatureVersion": "1",
                "Signature": "Jb7AzFgOzDXgsllGk04XJZQv3KF+2/JXziU2uFV6r5fti3GiLzQm9gZtx2imUuLCfNayFBRckzV3Q7ZxxxoUcebg0gG6Is0j/sVVHauLX/VhdkmyyjdkeJdqsnnBMOGCxiMXwO6YRAmTFM5Fx1WXiPLc5+TKoxxM1OmtPBkirmheJOpSzyvAX/BN8XdD+E/WjBtUZnc0qpy5kN/MVm6pwiNUNTZlMjBtPC8+qw9a04HGk2SkWb/nSksoYZnTnWDrxVu7lpQc7QnG2RA8KrevgisSyfMweeWKfQe1zRs6e+Uopepto48UsZ08A340kUcEsEdXf/XW5xMlPYrgIrTTXQ==",
                "SigningCertUrl": "https://sns.us-east-1.amazonaws.com/SimpleNotificationService-7ff5318490ec183fbaddaa2a969abfda.pem",
                "UnsubscribeUrl": "https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-east-1:123901341784:NewGFSObject:47c29dbe-6482-4495-bc25-41686b9c8f30",
                "MessageAttributes": {}
            }
        }
    ]
}, {})