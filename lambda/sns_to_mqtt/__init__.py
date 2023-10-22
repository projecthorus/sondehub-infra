import sys
sys.path.append("sns_to_mqtt/vendor")
import json
import os
import paho.mqtt.client as mqtt
import time
import random
import zlib
import base64
import boto3
import traceback
import sys
import uuid
import config_handler

client = mqtt.Client(transport="websockets")

connected_flag = False

import socket
socket.setdefaulttimeout(1)

logs = boto3.client('logs')
sequenceToken = None
log_stream_name = str(uuid.uuid4())

MAX_CACHE = 10000 # how many serials should we cache
cache = {}

def handle_error(message, event, stream_name):
    global sequenceToken
    print(message)
    events = [
                {
                    'timestamp': time.time_ns() // 1_000_000,
                    'message': message
                },
            ]
    if(event):
        events.insert(0, {
                        'timestamp': time.time_ns() // 1_000_000,
                        'message': json.dumps(event)
                    })
    if sequenceToken:
        response = logs.put_log_events(
            logGroupName='/sns_to_mqtt',
            logStreamName=stream_name,
            logEvents=events,
            sequenceToken=sequenceToken
        )
        sequenceToken = response['nextSequenceToken']
    else:
        try:
            log_stream = logs.create_log_stream(
            logGroupName='/sns_to_mqtt',
            logStreamName=stream_name
        )
        except: # ignore times we fail to create a log_stream - its probably already created
            pass
        response = logs.put_log_events(
            logGroupName='/sns_to_mqtt',
            logStreamName=stream_name,
            logEvents=events
        )
        sequenceToken = response['nextSequenceToken']
    print(sequenceToken)

def connect():
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish
    #client.tls_set()
    client.username_pw_set(username=config_handler.get("MQTT","USERNAME"), password=config_handler.get("MQTT","PASSWORD"))
    HOSTS = config_handler.get("MQTT","HOST").split(",")
    HOST = random.choice(HOSTS)
    print(f"Connecting to {HOST}",None,log_stream_name)
    client.connect(HOST, 8080, 5)
    client.loop_start()
    print("loop started",None,log_stream_name)

def on_disconnect(client, userdata, rc):
    global connected_flag
    print("disconnected", None, log_stream_name)
    connected_flag=False #set flag

def on_connect(client, userdata, flags, rc):
    global connected_flag
    if rc==0:
        print("connected", None, log_stream_name)
        connected_flag=True #set flag
    else:
        print("Bad connection Returned code=",rc, None, log_stream_name)

def on_publish(client, userdata, mid):
    pass

try:
    connect()
except:
    exc_type, exc_value, exc_traceback = sys.exc_info()
    handle_error("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)), None, log_stream_name)

def lambda_handler(event, context):
    try:
        client.loop(timeout=0.05, max_packets=1) # make sure it reconnects
        for record in event['Records']:
            sns_message = record["Sns"]
            try:
                decoded = json.loads(zlib.decompress(base64.b64decode(sns_message["Message"]), 16 + zlib.MAX_WBITS))
            except:
                decoded = json.loads(sns_message["Message"])

            if type(decoded) == dict:
                incoming_payloads = [decoded]
            else:
                incoming_payloads = decoded
            
            payloads = incoming_payloads
            for payload in payloads:
                
                body = json.dumps(payload)

                serial = payload[config_handler.get("MQTT","ID")]
                while not connected_flag:
                    time.sleep(0.01) # wait until connected
                client.publish(
                    topic=f'{config_handler.get("MQTT","PREFIX")}/{serial}',
                    payload=body,
                    qos=0,
                    retain=False
                )
                if serial not in cache: # low bandwidth feeds with just the first packet
                    client.publish(
                        topic=f'{config_handler.get("MQTT","PREFIX")}-new/{serial}',
                        payload=body,
                        qos=0,
                        retain=False
                    )
                    cache[serial] = body
                    # clean up cache if its too long
                    while len(cache) > MAX_CACHE:
                        del cache[next(iter(cache))]
            client.publish(
                topic=config_handler.get("MQTT","BATCH"),
                payload=json.dumps(payloads),
                qos=0,
                retain=False
            )
        time.sleep(0.05) # give paho mqtt 100ms to send messages this could be improved on but paho mqtt is a pain to interface with
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        handle_error("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)), event, log_stream_name)