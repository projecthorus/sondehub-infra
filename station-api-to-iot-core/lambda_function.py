import json
import boto3
import zlib
import base64
import datetime
import functools
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all
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


patch_all()


event_loop_group = io.EventLoopGroup(1)
host_resolver = io.DefaultHostResolver(event_loop_group)


io.init_logging(io.LogLevel.Error, "stderr")


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


if __name__ == "__main__":
    payload = {
        "version": "2.0",
        "routeKey": "PUT /sondes/telemetry",
        "rawPath": "/sondes/telemetry",
        "rawQueryString": "",
        "headers": {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate",
            "content-encoding": "gzip",
            "content-length": "2135",
            "content-type": "application/json",
            "host": "api.v2.sondehub.org",
            "user-agent": "autorx-1.4.1-beta4",
            "x-amzn-trace-id": "Root=1-6015f571-6aef2e73165042d53fcc317a",
            "x-forwarded-for": "103.107.130.22",
            "x-forwarded-port": "443",
            "x-forwarded-proto": "https",
            "date": "Sun, 31 Jan 2021 00:21:45 GMT",
        },
        "requestContext": {
            "accountId": "143841941773",
            "apiId": "r03szwwq41",
            "domainName": "api.v2.sondehub.org",
            "domainPrefix": "api",
            "http": {
                "method": "PUT",
                "path": "/sondes/telemetry",
                "protocol": "HTTP/1.1",
                "sourceIp": "103.107.130.22",
                "userAgent": "autorx-1.4.1-beta4",
            },
            "requestId": "Z_NJvh0RoAMEJaw=",
            "routeKey": "PUT /sondes/telemetry",
            "stage": "$default",
            "time": "31/Jan/2021:00:10:25 +0000",
            "timeEpoch": 1612051825409,
        },
        "body": "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",
        "isBase64Encoded": True,
    }
    lambda_handler(payload, {})
