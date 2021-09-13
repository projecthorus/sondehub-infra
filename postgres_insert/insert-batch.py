import logging
from urllib import parse
import boto3
from botocore.exceptions import ClientError
import json
logger = logging.getLogger(__name__)
logger.setLevel('DEBUG')

from botocore import UNSIGNED
from botocore.config import Config

s3 = boto3.client('s3', config=Config(signature_version=UNSIGNED))

import psycopg2
import psycopg2.extras
import os

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DATABASE = os.getenv("DB_DATABASE")

con = psycopg2.connect(database=DB_DATABASE, user=DB_USER,
                       password=DB_PASSWORD, host=DB_HOST, port="5432")


def lambda_handler(event, context):
    # Parse job parameters from Amazon S3 batch operations
    invocation_id = event['invocationId']
    invocation_schema_version = event['invocationSchemaVersion']

    results = []
    result_code = None
    result_string = None

    for task in event['tasks']:
        task_id = task['taskId']

        try:
            obj_key = parse.unquote(task['s3Key'], encoding='utf-8')
            bucket_name = task['s3BucketArn'].split(':')[-1]

            logger.info("Got task:  %s.", obj_key)

            response = s3.get_object(
                Bucket=bucket_name, Key=obj_key
            )

            payload = json.loads(response["Body"].read())

            try:
                    cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)
                    cur.execute(
                        """
                        INSERT INTO telemetry (datetime, serial, type, uploader_callsign, frame, frame_data, "position")
                        VALUES (%s, %s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s, %s), 4326)::Point);
                        """,
                        (payload["datetime"], payload["serial"], payload["type"], payload["uploader_callsign"], payload["frame"],json.dumps(payload), payload["lat"], payload["lon"], payload["alt"] )
                    )
                    con.commit()
                    result_code = 'Succeeded'
                    result_string = f"Successfully inserted into DB" \
                                    f" for object {obj_key}."
                    logger.info(result_string)
            except:
                    result_code = 'TemporaryFailure'
                    result_string = f"Attempt to insert  " \
                                    f"{obj_key}"
                    logger.info(result_string)
        except Exception as error:
            # Mark all other exceptions as permanent failures.
            result_code = 'PermanentFailure'
            result_string = str(error)
            logger.exception(error)
        finally:
            results.append({
                'taskId': task_id,
                'resultCode': result_code,
                'resultString': result_string
            })
    return {
        'invocationSchemaVersion': invocation_schema_version,
        'treatMissingKeysAs': 'PermanentFailure',
        'invocationId': invocation_id,
        'results': results
    }


if __name__ == "__main__":
    print(lambda_handler(
     
            {
                "invocationSchemaVersion": "1.0",
                "invocationId": "YXNkbGZqYWRmaiBhc2RmdW9hZHNmZGpmaGFzbGtkaGZza2RmaAo",
                "job": {
                    "id": "f3cc4f60-61f6-4a2b-8a21-d07600c373ce"
                },
                "tasks": [
                    {
                        "taskId": "dGFza2lkZ29lc2hlcmUK",
                        "s3Key": "date/1253-02-09T11:12:58.000000Z-17052971-982805f8-fa15-4183-b4a2-f1991b6d8f59.json",
                        "s3VersionId": "1",
                        "s3BucketArn": "arn:aws:s3:us-east-1:0123456788:sondehub-open-data"
                    }
                ]
            }, {}
    )
    )

