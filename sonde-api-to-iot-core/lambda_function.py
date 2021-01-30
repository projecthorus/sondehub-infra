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
client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)
credentials_provider = auth.AwsCredentialsProvider.new_default_chain(client_bootstrap)

io.init_logging(io.LogLevel.Info, 'stderr')

session = boto3.session.Session()
mqtt_connection = mqtt_connection_builder.websockets_with_default_aws_signing(
endpoint="a2sgq5szfqum7p-ats.iot.us-east-1.amazonaws.com",
client_bootstrap=client_bootstrap,
region="us-east-1",
credentials_provider=credentials_provider,
client_id=str(uuid.uuid4()),
clean_session=False,
keep_alive_secs=6)
connect_future = mqtt_connection.connect()

def lambda_handler(event, context):
    global connect_future, mqtt_connection

    # Future.result() waits until a result is available
    connect_future.result()

    print(json.dumps(event))
    if "isBase64Encoded" in event and event["isBase64Encoded"] == True:
        event["body"] = base64.b64decode(event["body"])
    if "content-encoding" in event["headers"] and event["headers"]["content-encoding"] == "gzip":
        event["body"] = zlib.decompress(event["body"], 16+zlib.MAX_WBITS)
        
    payloads = json.loads(event["body"])
    
    tasks = []
    first = False
    for payload in payloads:
        if "user-agent" in event["headers"]:
            event["time_server"] = datetime.datetime.now().isoformat()
            payload["user-agent"] = event["headers"]["user-agent"]
        payload["position"] = f'{payload["lat"]},{payload["lon"]}'
    
        (msg, x) = mqtt_connection.publish(
            topic=f'sondes/{payload["serial"]}',
            payload=json.dumps(payload),
            qos=mqtt.QoS.AT_MOST_ONCE)
        try:
            msg.result()
        except (RuntimeError, AwsCrtError):
            mqtt_connection = mqtt_connection_builder.websockets_with_default_aws_signing(
            endpoint="a2sgq5szfqum7p-ats.iot.us-east-1.amazonaws.com",
            client_bootstrap=client_bootstrap,
            region="us-east-1",
            credentials_provider=credentials_provider,
            client_id=str(uuid.uuid4()),
            clean_session=False,
            keep_alive_secs=6)
            connect_future = mqtt_connection.connect()
            connect_future.result()
            (msg, x) = mqtt_connection.publish(
            topic=f'sondes/{payload["serial"]}',
            payload=json.dumps(payload),
            qos=mqtt.QoS.AT_MOST_ONCE)
            msg.result()
    

    return {
        'statusCode': 200,
        'body': "^v^ telm logged"
    }

