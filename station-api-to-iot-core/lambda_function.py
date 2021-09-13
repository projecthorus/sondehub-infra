import json
import boto3
import zlib
import base64
import datetime
import functools
from awscrt import io, mqtt, auth, http
from awscrt.exceptions import AwsCrtError
from awsiot import mqtt_connection_builder
import uuid
import threading
from email.utils import parsedate
import os

# this needs a bunch of refactor but the general approach is
# connect to mqtt via websockets during init
# if we detect that we are disconnected then reconnect
# this is to make the lambda function nice and quick when during
# peak load

# todo
# we should add some value checking
# we typically perform version banning here based on user agent
# xray doesn't know about mqtt, we should teach it
# we should probably get sondehub v1 stuff in here as well
# error handling - at the moment we bail on a single failure
# report to the user what's happened
# probably turn down logging since cloudwatch costs $$$
# env variable some of this
# work out how to have a dev env



event_loop_group = io.EventLoopGroup(1)
host_resolver = io.DefaultHostResolver(event_loop_group)


def connect():
    global connect_future, mqtt_connection
    session = boto3.session.Session()
    client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)
    credentials_provider = auth.AwsCredentialsProvider.new_default_chain(
        client_bootstrap
    )
    mqtt_connection = mqtt_connection_builder.websockets_with_default_aws_signing(
        endpoint=os.getenv("IOT_ENDPOINT"),
        client_bootstrap=client_bootstrap,
        region="us-east-1",
        credentials_provider=credentials_provider,
        client_id=str(uuid.uuid4()),
        clean_session=False,
        keep_alive_secs=6,
    )
    connect_future = mqtt_connection.connect()
    connect_future.result()


connect()


def lambda_handler(event, context):

    # Future.result() waits until a result is available
    try:
        connect_future.result()
    except:
        connect()

    if "isBase64Encoded" in event and event["isBase64Encoded"] == True:
        event["body"] = base64.b64decode(event["body"])
    if (
        "content-encoding" in event["headers"]
        and event["headers"]["content-encoding"] == "gzip"
    ):
        event["body"] = zlib.decompress(event["body"], 16 + zlib.MAX_WBITS)
    time_delta = None
    if "date" in event["headers"]:
        try:
            time_delta_header = event["headers"]["date"]
            time_delta = (
                datetime.datetime(*parsedate(time_delta_header)[:7])
                - datetime.datetime.utcnow()
            ).total_seconds()
        except:
            pass
    payload = json.loads(event["body"])
    print(payload)
    tasks = []
    first = False
    if "user-agent" in event["headers"]:
        event["time_server"] = datetime.datetime.now().isoformat()
        payload["user-agent"] = event["headers"]["user-agent"]
    if time_delta:
        payload["upload_time_delta"] = time_delta
    (payload["uploader_alt"], payload["uploader_position_elk"]) = (
                payload["uploader_position"][2],
                f"{payload['uploader_position'][0]},{payload['uploader_position'][1]}",
            )
    (msg, x) = mqtt_connection.publish(
        topic=f'stations/station_position',
        payload=json.dumps(payload),
        qos=mqtt.QoS.AT_MOST_ONCE,
    )
    try:
        msg.result()
    except (RuntimeError, AwsCrtError):
        connect()
        (msg, x) = mqtt_connection.publish(
            topic=f'stations/station_position',
            payload=json.dumps(payload),
            qos=mqtt.QoS.AT_MOST_ONCE,
        )
        msg.result()

    return {"statusCode": 200, "body": "^v^ telm logged"}

