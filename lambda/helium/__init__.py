import json
import boto3
import zlib
import base64
import datetime
from email.utils import parsedate
import os

HELIUM_GW_VERSION = "2023.08.25"

def set_connection_header(request, operation_name, **kwargs):
    request.headers['Connection'] = 'keep-alive'

sns = boto3.client("sns",region_name="us-east-1")
sns.meta.events.register('request-created.sns', set_connection_header)



def post(payload):
    sns.publish(
                TopicArn=os.getenv("HAM_SNS_TOPIC"),
                Message=json.dumps(payload)
    )

def upload(event, context):
    if "isBase64Encoded" in event and event["isBase64Encoded"] == True:
        event["body"] = base64.b64decode(event["body"])
    if (
        "content-encoding" in event["headers"]
        and event["headers"]["content-encoding"] == "gzip"
    ):
        event["body"] = zlib.decompress(event["body"], 16 + zlib.MAX_WBITS)

    payloads = json.loads(event["body"])
    to_sns = []
    errors = []
    warnings = []


    # If only have one object, turn it into a single-entry list.
    if type(payloads) == dict:
        payloads = [payloads]

    # Iterate over list:
    for payload in payloads:

        try:
            telem = {
                'software_name': 'SondeHub-Amateur Helium Gateway',
                'software_version': HELIUM_GW_VERSION
            }

            #
            # Extract mandatory fields.
            #
            # Name -> Payload Callsign
            telem['payload_callsign'] = payload['name']

            # Time
            telem['datetime'] = datetime.datetime.utcfromtimestamp(payload["reported_at"]/1000.0).isoformat() + "Z"

            # Positional and other data
            telem_data = payload["decoded"]["payload"]

            # Position
            telem["position"] = f'{telem_data["latitude"]},{telem_data["longitude"]}'
            telem["lat"] = telem_data['latitude']
            telem["lon"] = telem_data['longitude']
            telem["alt"] = telem_data['altitude']

            #
            # Other optional fields
            #
            if 'sats' in telem_data:
                telem["sats"] = telem_data["sats"]
            
            if 'battery' in telem_data:
                telem["batt"] = telem_data["battery"]

            if 'batt' in telem_data:
                telem["batt"] = telem_data["batt"]

            if 'speed' in telem_data:
                telem['speed'] = telem_data['speed']

            if 'temperature' in telem_data:
                telem['temp'] = telem_data['temperature']

            if 'temp' in telem_data:
                telem['temp'] = telem_data['temp']

            if 'ext_temperature' in telem_data:
                telem['ext_temperature'] = telem_data['ext_temperature']

            if 'ext_pressure' in telem_data:
                telem['ext_pressure'] = telem_data['ext_pressure']

            if 'ext_humidity' in telem_data:
                telem['ext_humidity'] = telem_data['ext_humidity']

            if 'accel_x' in telem_data:
                telem['accel_x'] = telem_data['accel_x']
            
            if 'accel_y' in telem_data:
                telem['accel_y'] = telem_data['accel_y']

            if 'accel_z' in telem_data:
                telem['accel_z'] = telem_data['accel_z']

            # Base64-encoded raw and payload packet data
            if 'raw_packet' in payload:
                telem['raw'] = payload['raw_packet']

            if 'payload' in payload:
                telem['raw_payload'] = payload['payload']
        
        except Exception as e:
            errors.append({
                "error_message": f"Error parsing telemetry data - {str(e)}",
                "payload": payload
            })
            continue

        # Now iterate through the receiving stations
        for hotspot in payload['hotspots']:
            try:
                hotspot_telem = telem.copy()

                hotspot_telem['uploader_callsign'] = hotspot['name']
                hotspot_telem['modulation'] = f"Helium ({hotspot['spreading']})"
                hotspot_telem['snr'] = hotspot['snr']
                hotspot_telem['rssi'] = hotspot['rssi']
                hotspot_telem['frequency'] = hotspot['frequency']
                hotspot_telem['time_received'] = datetime.datetime.utcfromtimestamp(hotspot["reported_at"]/1000.0).isoformat() + "Z"

                try:
                    hotspot_telem['uploader_position'] = f'{hotspot["lat"]},{hotspot["long"]}'
                    hotspot_telem['uploader_alt'] = 0
                except:
                    pass

                
                to_sns.append(hotspot_telem)

            except Exception as e:
                errors.append({
                "error_message": f"Error parsing hotspot data - {str(e)}",
                "payload": payload
                })
                continue
    
    #print(to_sns)

    post(to_sns)
    return errors, warnings


def lambda_handler(event, context):
    try:
        errors, warnings = upload(event, context)
    except zlib.error:
        return {"statusCode": 400, "body": "Could not decompress"}
    except json.decoder.JSONDecodeError:
        return {"statusCode": 400, "body": "Not valid json"}
    error_message = {
        "message": "some or all payloads could not be processed or have warnings",
        "errors": errors,
        "warnings": warnings
    }
    if errors or warnings:
        output = {
            "statusCode": 202, 
            "body": json.dumps(error_message),
            "headers": {
                "content-type": "application/json"
            }
        }
        print({
            "statusCode": 202, 
            "body": error_message,
            "headers": {
                "content-type": "application/json"
            }
        })
        return output
    else:
        return {"statusCode": 200, "body": "^v^ telm logged"}

