import sys
sys.path.append("sns_to_mqtt/vendor")
import json
import os
import paho.mqtt.client as mqtt
import time

client = mqtt.Client(transport="websockets")

connected_flag = False

def connect():
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish
    client.tls_set()
    client.username_pw_set(username=os.getenv("MQTT_USERNAME"), password=os.getenv("MQTT_PASSWORD"))
    client.connect(os.getenv("MQTT_HOST"), 443, 5)
    client.loop_start()
    print("loop started")

def on_disconnect(client, userdata, rc):
    global connected_flag
    print("disconnected")
    connected_flag=False #set flag

def on_connect(client, userdata, flags, rc):
    global connected_flag
    if rc==0:
        print("connected")
        connected_flag=True #set flag
    else:
        print("Bad connection Returned code=",rc)

def on_publish(client, userdata, mid):
    pass

connect()

def lambda_handler(event, context):
    client.loop(timeout=0.05, max_packets=1) # make sure it reconnects
    for record in event['Records']:
        sns_message = record["Sns"]
        if type(json.loads(sns_message["Message"])) == dict:
            incoming_payloads = [json.loads(sns_message["Message"])]
        else:
            incoming_payloads = json.loads(sns_message["Message"])
        
        #send only the first, last and every 5th packet
        payloads = [incoming_payloads[0]] + incoming_payloads[1:-1:5][1:] + [incoming_payloads[-1]]
        for payload in payloads:
            
            body = json.dumps(payload)

            serial = payload[os.getenv("MQTT_ID")]
            while not connected_flag:
                time.sleep(0.01) # wait until connected
            client.publish(
                topic=f'{os.getenv("MQTT_PREFIX")}/{serial}',
                payload=body,
                qos=0,
                retain=False
            )
        client.publish(
            topic=f'batch',
            payload=json.dumps(payloads),
            qos=0,
            retain=False
        )
    time.sleep(0.05) # give paho mqtt 100ms to send messages this could be improved on but paho mqtt is a pain to interface with
    

