import json
import boto3
import zlib
import base64
import datetime
from email.utils import parsedate
import os
import config_handler

HELIUM_GW_VERSION = "2023.10.14"

# Mappings between input (Helium) field names, and field names fed into SondeHub-Amateur
FIELD_MAPPINGS = [
    ['lat',         'lat'],
    ['lon',         'lon'],
    ['alt',         'alt'],
    ['latitude',    'lat'],
    ['longitude',   'lon'],
    ['altitude',    'alt'],
    ['sats',        'sats'],
    ['battery',     'batt'],
    ['batt',        'batt'],
    ['speed',       'speed'],
    ['heading',     'heading'],
    ['temp',        'temp'],
    ['temperature', 'temp'],
    ['ext_temperature', 'ext_temperature'],
    ['ext_pressure','ext_pressure'],
    ['pressure',    'ext_pressure'],
    ['ext_humidity','ext_humidity'],
    ['accel_x',     'accel_x'],
    ['accel_y',     'accel_y'],
    ['accel_z',     'accel_z'],
    ['gyro_x',      'gyro_x'],
    ['gyro_y',      'gyro_y'],
    ['gyro_z',      'gyro_z'],
    ['illuminance', 'illuminance']
]


def set_connection_header(request, operation_name, **kwargs):
    request.headers['Connection'] = 'keep-alive'

sns = boto3.client("sns",region_name="us-east-1")
sns.meta.events.register('request-created.sns', set_connection_header)


def post(payload):
    sns.publish(
                TopicArn=config_handler.get("HAM_SNS","TOPIC"),
                Message=json.dumps(payload)
    )


def upload_helium(event, context):
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

            # Work through all accepted field names and map them
            # into the output structure.
            for _field in FIELD_MAPPINGS:
                _input = _field[0]
                _output = _field[1]

                if _input in telem_data:
                    telem[_output] = telem_data[_input]

            # Position field, required by OpenSearch
            # If lat/lon are not in the telemetry, then this will error
            telem["position"] = f'{telem["lat"]},{telem["lon"]}'

            # We also need altitude as a minimum
            if 'alt' not in telem:
                raise IOError("No altitude field")
        
            # Extract raw payload data, base64
            telem["raw"] = payload["payload"]

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


def upload_ttn(event, context):
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
                'software_name': 'SondeHub-Amateur TTN Gateway',
                'software_version': HELIUM_GW_VERSION
            }

            #
            # Extract mandatory fields.
            #
            # Name -> Payload Callsign
            telem['payload_callsign'] = payload['end_device_ids']['application_ids']['application_id']

            # Time
            telem['datetime'] = payload['received_at']

            # Positional and other data
            telem_data = payload["uplink_message"]["decoded_payload"]

            # Work through all accepted field names and map them
            # into the output structure.
            for _field in FIELD_MAPPINGS:
                _input = _field[0]
                _output = _field[1]

                if _input in telem_data:
                    telem[_output] = telem_data[_input]

            # Position field, required by OpenSearch
            # If lat/lon are not in the telemetry, then this will error
            telem["position"] = f'{telem["lat"]},{telem["lon"]}'

            # We also need altitude as a minimum
            if 'alt' not in telem:
                raise IOError("No altitude field")
            
            # Extract raw payload data, base64
            telem["raw"] = payload["uplink_message"]["frm_payload"]
        
        except Exception as e:
            errors.append({
                "error_message": f"Error parsing telemetry data - {str(e)}",
                "payload": payload
            })
            continue

        # Now iterate through the receiving stations
        for hotspot in payload['uplink_message']['rx_metadata']:
            try:
                hotspot_telem = telem.copy()

                hotspot_telem['uploader_callsign'] = hotspot['gateway_ids']['gateway_id']

                # Frequency and modulation metadata is common to all packets
                # Frequency is in Hz
                hotspot_telem['frequency'] = float(payload['uplink_message']['settings']['frequency'])/1e6

                # Construct the lora modulation details.
                _bw = int( int(payload['uplink_message']['settings']['data_rate']['lora']['bandwidth']) / 1000)
                _sf = int(payload['uplink_message']['settings']['data_rate']['lora']['spreading_factor'])
                _cr = payload['uplink_message']['settings']['data_rate']['lora']['coding_rate'].replace('/','')
                hotspot_telem['modulation'] = f"TTN (SF{_sf}BW{_bw}CR{_cr})"

                # SNR and RSSI is unique to each receiver
                hotspot_telem['snr'] = hotspot['snr']
                hotspot_telem['rssi'] = hotspot['rssi']
                # There is also a channel_rssi field that we could include...

                # Can't seem to trust the timestamp in the per-receiver metadata
                # Example input has some very wrong timestamps in it.
                hotspot_telem['time_received'] = payload['received_at']
                
                try:
                    hotspot_telem['uploader_position'] = f'{hotspot["location"]["latitude"]},{hotspot["location"]["longitude"]}'
                    if 'altitude' in hotspot["location"]:
                        hotspot_telem['uploader_alt'] = hotspot["location"]["altitude"]
                    else:
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


def lambda_handler(event, context, ttn_source=False):
    try:
        if ttn_source:
            errors, warnings = upload_ttn(event, context)
        else:
            errors, warnings = upload_helium(event, context)
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

def lambda_handler_helium(event, context):
    return lambda_handler(event, context)

def lambda_handler_ttn(event, context):
    return lambda_handler(event, context, ttn_source=True)