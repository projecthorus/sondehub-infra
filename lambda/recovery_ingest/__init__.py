from datetime import datetime
import urllib.request
import json
import config_handler
import traceback

apiKey = config_handler.get("RADIOSONDY","API_KEY")

params = "?token={}&period=2".format(apiKey)
url = "https://radiosondy.info/api/v1/sonde-logs{}".format(params)
recoveryUrl = "https://api.v2.sondehub.org/recovered"
searchUrl = "https://api.v2.sondehub.org/sondes"

# Main function
def handler(event,context):
    response = urllib.request.urlopen(url)
    data = json.load(response)
    processReports(data)

# Check exisiting SondeHub recovery reports
def checkExisting(serial, recovered):
    # Get SondeHub recoveries for serial
    recoveryCheckParams = "?serial={}".format(serial)
    recoveryCheckUrl = recoveryUrl + recoveryCheckParams
    recoveryCheckResponse = urllib.request.urlopen(recoveryCheckUrl)
    recoveryCheckData = json.load(recoveryCheckResponse)

    # No recovery reports for serial
    if len(recoveryCheckData) == 0:
        return True

    # Not recovered report and we have recovered
    if recoveryCheckData[0]["recovered"] == False and recovered == True:
        return True

    # Valid recovery report already exists
    return False

# Attempt to find SondeHub serial for a Radiosony.info serial
def findSonde(recovery, lat, lon):
    # Get facts to compare against
    launchTime = datetime.strptime(recovery["start_time"], "%Y-%m-%d %H:%M:%S")
    sondeType = recovery["radiosonde"]["type"]
    sondeFrequency = recovery["radiosonde"]["qrg"]

    # Determine how far back to query
    nowTime = datetime.utcnow()
    searchDifference = nowTime - launchTime
    searchSeconds = round(searchDifference.total_seconds()) + 10800 # Search from 3 hours before reported launch

    # Geographical SondeHub search
    searchParams = "?lat={}&lon={}&distance=2000&last={}".format(lat, lon, searchSeconds)
    searchCompletedUrl = searchUrl + searchParams
    searchResponse = urllib.request.urlopen(searchCompletedUrl)
    searchData = json.load(searchResponse)

    serial = None

    # Check all returned sondes
    for key, value in searchData.items():
        receivedTime = datetime.strptime(value["datetime"], "%Y-%m-%dT%H:%M:%S.%fZ")
        timeDifference = receivedTime - launchTime
        if timeDifference.total_seconds() < 10800: # 3 Hours or less
            if value["type"] in sondeType: # Type matches
                if abs(float(sondeFrequency) - float(value["frequency"])) < 0.05: # 0.05 MHz or less
                    serial = key

    return serial

# Process each recovery report from Radiosondy.info
def processReports(data):
    for recovery in data["results"]:
        try:

            # Get recovery status
            if recovery["log_info"]["status"] == "FOUND":
                recovered = True
            elif recovery["log_info"]["status"] == "NEED ATTENTION":
                recovered = False
            elif recovery["log_info"]["status"] == "LOST":
                recovered = False
            else:
                continue

            # Get finder if available
            if recovery["log_info"]["finder"] is not None:
                recovered_by = recovery["log_info"]["finder"]
            elif "[BOT]" not in recovery["log_info"]["added_by"]:
                recovered_by = recovery["log_info"]["added_by"]
            else:
                continue

            # Import time
            recovered_time = datetime.strptime(recovery["log_info"]["log_added"], "%Y-%m-%d %H:%M:%S")

            # Get comment and add attribution
            description = recovery["log_info"]["comment"]
            description += " [via Radiosondy.info]"
            description = description.lstrip()

            if recovery["log_info"]["found_coordinates"]["latitude"] != "0" and recovery["log_info"]["found_coordinates"]["longitude"] != "0":
                lat = float(recovery["log_info"]["found_coordinates"]["latitude"])
                lon = float(recovery["log_info"]["found_coordinates"]["longitude"])
            else:
                continue

            # Use the reported serial number for RS41/RS92
            if "RS41" in recovery["radiosonde"]["type"] or "RS92" in recovery["radiosonde"]["type"]:
                serial = recovery["radiosonde"]["number"]
            # Remove D prefix for DFM
            elif "DFM" in recovery["radiosonde"]["type"]:
                serial = recovery["radiosonde"]["number"][1:]
            # Try to find serial in SondeHub database for others
            else:
                serial = findSonde(recovery, lat, lon)
                if serial is None:
                    print("{}: could not match to SondeHub serial".format(recovery["radiosonde"]["number"]))
                    continue

            # Check if a valid recovery already exists
            if checkExisting(serial, recovered) == False:
                print("{}: recovery already exists".format(serial))
                continue

            # Format data for upload
            recoveryPutData = {"datetime": recovered_time.isoformat(), "serial": serial, "lat": lat, "lon": lon, "recovered": recovered, "recovered_by": recovered_by, "description": description}
            recoveryPutData = json.dumps(recoveryPutData, ensure_ascii=True).encode('utf-8')
            print("{}: {}".format(serial, recoveryPutData))
            
            # Upload data
            recoveryPutRequest = urllib.request.Request(recoveryUrl, data=recoveryPutData, method="PUT")
            print("{}: {}".format(serial, urllib.request.urlopen(recoveryPutRequest).read().decode('utf-8')))
        except:
            traceback.print_exc()