import json
from datetime import datetime
import http.client
import math
import logging
from math import radians, degrees, sin, cos, atan2, sqrt, pi
import es
import asyncio
import functools


#   FLIGHT PROFILE DEFAULTS
#

# If we have no better estimates for flight profile, use these:
PREDICT_DEFAULTS = {'ascent_rate': 5.0, 'burst_altitude': 26000.0, 'descent_rate': 6.0}

# For some sonde types we can make better assumptions
SONDE_TYPE_PREDICT_DEFAULTS = {
}

#
#   LAUNCH SITE ALLOCATION SETTINGS
#
# Immediately allocate a launch site if it is within this distance (straight line)
# of a known launch site.
LAUNCH_ALLOCATE_RANGE_MIN = 4000 # metres
LAUNCH_ALLOCATE_RANGE_MAX = 30000 # metres
LAUNCH_ALLOCATE_RANGE_SCALING = 1.5 # Scaling factor - launch allocation range is min(current alt * this value , launch allocate range max)

# Do not run predictions if the ascent or descent rate is less than this value
ASCENT_RATE_THRESHOLD = 0.8

def flight_profile_by_type(sonde_type):
    """
    Determine the appropriate flight profile based on radiosonde type
    """

    for _def_type in SONDE_TYPE_PREDICT_DEFAULTS:
        if _def_type in sonde_type:
            return SONDE_TYPE_PREDICT_DEFAULTS[_def_type].copy()
    
    return PREDICT_DEFAULTS.copy()


def getDensity(altitude):
    """ 
	Calculate the atmospheric density for a given altitude in metres.
	This is a direct port of the oziplotter Atmosphere class
	"""

    # Constants
    airMolWeight = 28.9644  # Molecular weight of air
    densitySL = 1.225  # Density at sea level [kg/m3]
    pressureSL = 101325  # Pressure at sea level [Pa]
    temperatureSL = 288.15  # Temperature at sea level [deg K]
    gamma = 1.4
    gravity = 9.80665  # Acceleration of gravity [m/s2]
    tempGrad = -0.0065  # Temperature gradient [deg K/m]
    RGas = 8.31432  # Gas constant [kg/Mol/K]
    R = 287.053
    deltaTemperature = 0.0

    # Lookup Tables
    altitudes = [0, 11000, 20000, 32000, 47000, 51000, 71000, 84852]
    pressureRels = [
        1,
        2.23361105092158e-1,
        5.403295010784876e-2,
        8.566678359291667e-3,
        1.0945601337771144e-3,
        6.606353132858367e-4,
        3.904683373343926e-5,
        3.6850095235747942e-6,
    ]
    temperatures = [288.15, 216.65, 216.65, 228.65, 270.65, 270.65, 214.65, 186.946]
    tempGrads = [-6.5, 0, 1, 2.8, 0, -2.8, -2, 0]
    gMR = gravity * airMolWeight / RGas

    # Pick a region to work in
    i = 0
    if altitude > 0:
        while altitude > altitudes[i + 1]:
            i = i + 1

    # Lookup based on region
    baseTemp = temperatures[i]
    tempGrad = tempGrads[i] / 1000.0
    pressureRelBase = pressureRels[i]
    deltaAltitude = altitude - altitudes[i]
    temperature = baseTemp + tempGrad * deltaAltitude

    # Calculate relative pressure
    if math.fabs(tempGrad) < 1e-10:
        pressureRel = pressureRelBase * math.exp(
            -1 * gMR * deltaAltitude / 1000.0 / baseTemp
        )
    else:
        pressureRel = pressureRelBase * math.pow(
            baseTemp / temperature, gMR / tempGrad / 1000.0
        )

    # Add temperature offset
    temperature = temperature + deltaTemperature

    # Finally, work out the density...
    speedOfSound = math.sqrt(gamma * R * temperature)
    pressure = pressureRel * pressureSL
    density = densitySL * pressureRel * temperatureSL / temperature

    return density


def seaLevelDescentRate(descent_rate, altitude):
    """ Calculate the descent rate at sea level, for a given descent rate at altitude """

    rho = getDensity(altitude)
    return math.sqrt((rho / 1.225) * math.pow(descent_rate, 2))


# Earthmaths code by Daniel Richman (thanks!)
# Copyright 2012 (C) Daniel Richman; GNU GPL 3
def position_info(listener, balloon):
    """
    Calculate and return information from 2 (lat, lon, alt) tuples

    Returns a dict with:

     - angle at centre
     - great circle distance
     - distance in a straight line
     - bearing (azimuth or initial course)
     - elevation (altitude)

    Input and output latitudes, longitudes, angles, bearings and elevations are
    in degrees, and input altitudes and output distances are in meters.
    """

    # Earth:
    radius = 6371000.0

    (lat1, lon1, alt1) = listener
    (lat2, lon2, alt2) = balloon

    lat1 = radians(lat1)
    lat2 = radians(lat2)
    lon1 = radians(lon1)
    lon2 = radians(lon2)

    # Calculate the bearing, the angle at the centre, and the great circle
    # distance using Vincenty's_formulae with f = 0 (a sphere). See
    # http://en.wikipedia.org/wiki/Great_circle_distance#Formulas and
    # http://en.wikipedia.org/wiki/Great-circle_navigation and
    # http://en.wikipedia.org/wiki/Vincenty%27s_formulae
    d_lon = lon2 - lon1
    sa = cos(lat2) * sin(d_lon)
    sb = (cos(lat1) * sin(lat2)) - (sin(lat1) * cos(lat2) * cos(d_lon))
    bearing = atan2(sa, sb)
    aa = sqrt((sa ** 2) + (sb ** 2))
    ab = (sin(lat1) * sin(lat2)) + (cos(lat1) * cos(lat2) * cos(d_lon))
    angle_at_centre = atan2(aa, ab)
    great_circle_distance = angle_at_centre * radius

    # Armed with the angle at the centre, calculating the remaining items
    # is a simple 2D triangley circley problem:

    # Use the triangle with sides (r + alt1), (r + alt2), distance in a
    # straight line. The angle between (r + alt1) and (r + alt2) is the
    # angle at the centre. The angle between distance in a straight line and
    # (r + alt1) is the elevation plus pi/2.

    # Use sum of angle in a triangle to express the third angle in terms
    # of the other two. Use sine rule on sides (r + alt1) and (r + alt2),
    # expand with compound angle formulae and solve for tan elevation by
    # dividing both sides by cos elevation
    ta = radius + alt1
    tb = radius + alt2
    ea = (cos(angle_at_centre) * tb) - ta
    eb = sin(angle_at_centre) * tb
    elevation = atan2(ea, eb)

    # Use cosine rule to find unknown side.
    distance = sqrt((ta ** 2) + (tb ** 2) - 2 * tb * ta * cos(angle_at_centre))

    # Give a bearing in range 0 <= b < 2pi
    if bearing < 0:
        bearing += 2 * pi

    return {
        "listener": listener,
        "balloon": balloon,
        "listener_radians": (lat1, lon1, alt1),
        "balloon_radians": (lat2, lon2, alt2),
        "angle_at_centre": degrees(angle_at_centre),
        "angle_at_centre_radians": angle_at_centre,
        "bearing": degrees(bearing),
        "bearing_radians": bearing,
        "great_circle_distance": great_circle_distance,
        "straight_distance": distance,
        "elevation": degrees(elevation),
        "elevation_radians": elevation,
    }


def get_standard_prediction(timestamp, latitude, longitude, altitude, current_rate=5.0, ascent_rate=PREDICT_DEFAULTS['ascent_rate'], burst_altitude=PREDICT_DEFAULTS['burst_altitude'], descent_rate=PREDICT_DEFAULTS['descent_rate']):
    """
    Request a standard flight path prediction from Tawhiri.
    Notes:
    - The burst_altitude must be higher than the current altitude.
    - Longitude is in the range 0-360.0
    - All ascent/descent rates must be positive.
    """

    # Bomb out if the rates are too low.
    if ascent_rate < ASCENT_RATE_THRESHOLD:
        return None

    if descent_rate < ASCENT_RATE_THRESHOLD:
        return None


    # Shift longitude into the appropriate range for Tawhiri
    if longitude < 0:
        longitude += 360.0

    # Generate the prediction URL
    url = f"/api/v1/?launch_latitude={latitude}&launch_longitude={longitude}&launch_datetime={timestamp}&launch_altitude={altitude:.2f}&ascent_rate={ascent_rate:.2f}&burst_altitude={burst_altitude:.2f}&descent_rate={descent_rate:.2f}"
    logging.debug(url)
    conn = http.client.HTTPSConnection("tawhiri.v2.sondehub.org")
    conn.request("GET", url)
    res = conn.getresponse()
    data = res.read()

    if res.code != 200:
        logging.debug(data)
        return None
    
    pred_data = json.loads(data.decode("utf-8"))

    path = []

    if 'prediction' in pred_data:
        for stage in pred_data['prediction']:
            # Probably don't need to worry about this, it should only result in one or two points
            # in 'ascent'.
            if stage['stage'] == 'ascent' and current_rate < 0: # ignore ascent stage if we have already burst
                continue
            else:
                for item in stage['trajectory']:
                    path.append({
                        "time": int(datetime.fromisoformat(item['datetime'].split(".")[0].replace("Z","")).timestamp()),
                        "lat": item['latitude'],
                        "lon": item['longitude'] - 360 if item['longitude'] > 180 else item['longitude'],
                        "alt": item['altitude'],
                    })
        
        pred_data['path'] = path
        return pred_data
    else:
        return None



def bulk_upload_es(index_prefix,payloads):
    body=""
    for payload in payloads:
        body += "{\"index\":{}}\n" + json.dumps(payload) + "\n"
    body += "\n"
    date_prefix = datetime.now().strftime("%Y-%m")
    result = es.request(body, f"{index_prefix}-{date_prefix}/_doc/_bulk", "POST")

    if 'errors' in result and result['errors'] == True:
        error_types = [x['index']['error']['type'] for x in result['items'] if 'error' in x['index']] # get all the error types
        error_types = [a for a in error_types if a != 'mapper_parsing_exception'] # filter out mapper failures since they will never succeed
        if error_types:
            print(result)
            raise RuntimeError

def predict(event, context):
    # Use asyncio.run to synchronously "await" an async function
    result = asyncio.run(predict_async(event, context))
    return result

async def predict_async(event, context):
    sem = asyncio.Semaphore(5)
    path = "ham-telm-*/_search"
    interval = 60 # because some aprs balloons are only every minute
    lag = 3 # how many samples to use
    payload = {
                "aggs": {
                    "2": {
                    "terms": {
                        "field": "payload_callsign.keyword",
                        "order": {
                        "_key": "desc"
                        },
                        "size": 1000
                    },
                    "aggs": {
                        "3": {
                        "date_histogram": {
                            "field": "datetime",
                            "fixed_interval": f"{interval}s"
                        },
                        "aggs": {
                            "1": {
                            "top_hits": {
                                "docvalue_fields": [
                                {
                                    "field": "alt"
                                }
                                ],
                                "_source": "alt",
                                "size": 1,
                                "sort": [
                                {
                                    "datetime": {
                                    "order": "desc"
                                    }
                                }
                                ]
                            }
                            },
                            "4": {
                            "serial_diff": {
                                "buckets_path": "4-metric",
                                "gap_policy": "skip",
                                "lag": lag
                            }
                            },
                            "5": {
                            "top_hits": {
                                "docvalue_fields": [
                                {
                                    "field": "position"
                                }
                                ],
                                "_source": {"includes": ["position", "type", "subtype"]},
                                "size": 1,
                                "sort": [
                                {
                                    "datetime": {
                                    "order": "desc"
                                    }
                                }
                                ]
                            }
                            },
                            "4-metric": {
                            "avg": {
                                "field": "alt"
                            }
                            }
                        }
                        }
                    }
                    }
                },
                "size": 0,
                "stored_fields": [
                    "*"
                ],
                "script_fields": {},
                "docvalue_fields": [
                    {
                    "field": "@timestamp",
                    "format": "date_time"
                    },
                    {
                    "field": "datetime",
                    "format": "date_time"
                    },
                    {
                    "field": "log_date",
                    "format": "date_time"
                    },
                    {
                    "field": "time_received",
                    "format": "date_time"
                    },
                    {
                    "field": "time_server",
                    "format": "date_time"
                    },
                    {
                    "field": "time_uploaded",
                    "format": "date_time"
                    }
                ],
                "_source": {
                    "excludes": []
                },
                "query": {
                    "bool": {
                    "must": [],
                    "filter": [
                        {
                        "match_all": {}
                        },
                        {
                        "range": {
                            "datetime": {
                                    "gte": "now-10m",
                                    "lte": "now",
                            "format": "strict_date_optional_time"
                            }
                        }
                        }
                    ],
                    "should": [],
                    "must_not": [
                    {
                        "match_phrase": {
                            "software_name": "SondehubV1"
                        }
                    }
                ]
                    }
                },
                "size": 0
            }
    logging.debug("Start ES Request")
    results = es.request(json.dumps(payload), path, "GET")
    logging.debug("Finished ES Request")
    


    serials = { }
    for x in results['aggregations']['2']['buckets']:
        try:
            serials[x['key']] = {
                "alt": sorted(x['3']['buckets'], key=lambda k: k['key_as_string'])[-1]['1']['hits']['hits'][0]['fields']['alt'][0],
                "position": sorted(x['3']['buckets'], key=lambda k: k['key_as_string'])[-1]['5']['hits']['hits'][0]['fields']['position'][0].split(","),
                "rate": sorted(x['3']['buckets'], key=lambda k: k['key_as_string'])[-1]['4']['value']/(lag*interval), # as we bucket for every 5 seconds with a lag of 5
                "time": sorted(x['3']['buckets'], key=lambda k: k['key_as_string'])[-1]['key_as_string']
            
            }
        except:
            pass

    


    serial_data={}
    logging.debug("Start Predict")
    jobs=[]
    for serial in serials:
        jobs.append(run_predictions_for_serial(sem, serial, serials[serial]))
    output = await asyncio.gather(*jobs)
    for data in output:
        if data:
            serial_data[data[0]] = data[1]




    logging.debug("Stop Predict")

    # Collate and upload forward predictions
    output = []
    for serial in serial_data:
        value = serial_data[serial]

        if value is not None:
            output.append(
                {
                    "payload_callsign": serial,
                    "datetime": value['request']['launch_datetime'],
                    "position": [
                            value['request']['launch_longitude'] - 360 if value['request']['launch_longitude'] > 180 else value['request']['launch_longitude'],
                            value['request']['launch_latitude']
                        ],
                    "altitude": value['request']['launch_altitude'],
                    "ascent_rate": value['request']['ascent_rate'],
                    "descent_rate": value['request']['descent_rate'],
                    "burst_altitude": value['request']['burst_altitude'],
                    "descending": True if serials[serial]['rate'] < 0 else False,
                    "landed": False, # I don't think this gets used anywhere?
                    "data": value['path']
                }
            )

    if len(output) > 0:
        bulk_upload_es("ham-predictions", output)


    logging.debug("Finished")
    return



async def run_predictions_for_serial(sem, serial, value):
    async with sem:
        loop = asyncio.get_event_loop()
        #
        # Flight Profile selection 
        #
        # Fallback Option - use flight profile data based on sonde type.
        _flight_profile = flight_profile_by_type("")

        #print(value)
        #print(_flight_profile)
        logging.debug(f"Running prediction for {serial} using flight profile {str(_flight_profile)}.")

        # skip when close to 0.
        if value['rate'] < ASCENT_RATE_THRESHOLD and value['rate'] > -ASCENT_RATE_THRESHOLD:
            logging.debug(f"Skipping {serial} due to ascent rate limiting.")
            return False 

        # Determine current ascent rate
        # If the value is < 0.5 (e.g. we are on descent, or not moving), we just use a default value.
        ascent_rate=value['rate'] if value['rate'] > ASCENT_RATE_THRESHOLD else _flight_profile['ascent_rate']
        
        # If we are on descent, estimate the sea-level descent rate from the current descent rate
        # Otherwise, use the flight profile descent rate 
        descent_rate= seaLevelDescentRate(abs(value['rate']),value['alt']) if value['rate'] < 0 else _flight_profile['descent_rate']

        # If the resultant sea-level descent rate is very small, it means we're probably landed
        # so dont run a prediction for this sonde.
        if descent_rate < ASCENT_RATE_THRESHOLD:
            return False

        # Now to determine the burst altitude
        if value['rate'] < 0:
            # On descent (rate < 0), we need to set the burst altitude just higher than our current altitude for
            # the predictor to be happy
            burst_altitude = value['alt']+0.05
        else:
            # Otherwise, on ascent we either use the expected burst altitude, or we 
            # add a little bit on to our current altitude.
            burst_altitude = (value['alt']+0.05) if value['alt'] > _flight_profile['burst_altitude'] else _flight_profile['burst_altitude']

        longitude = float(value['position'][1].strip())
        latitude = float(value['position'][0].strip())

        #print(f"Prediction Parameters for {serial} at {latitude}, {longitude}, {value['alt']}: {ascent_rate}/{burst_altitude}/{descent_rate}")

        # Run prediction! This will return None if there is an error
        return [serial, await loop.run_in_executor(None, functools.partial(get_standard_prediction, 
            value['time'], 
            latitude,
            longitude,
            value['alt'],
            current_rate=value['rate'],
            ascent_rate=ascent_rate,
            burst_altitude=burst_altitude,
            descent_rate=descent_rate
            ))]

