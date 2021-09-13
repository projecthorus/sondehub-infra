import psycopg2
import psycopg2.extras
import os
import json

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_DATABASE = os.getenv("DB_DATABASE")

con = psycopg2.connect(database=DB_DATABASE, user=DB_USER,
                       password=DB_PASSWORD, host=DB_HOST, port="5432")


def main(event, context):
    cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(
        """
        INSERT INTO telemetry (datetime, serial, type, uploader_callsign, frame, frame_data, "position")
        VALUES (%s, %s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s, %s), 4326)::Point);
        """,
        (event["datetime"], event["serial"], event["type"], event["uploader_callsign"], event["frame"],json.dumps(event), event["lat"], event["lon"], event["alt"] )
    )
    con.commit()
    cur.close()


if __name__ == "__main__":
    main(
        {
            "software_name": "radiosonde_auto_rx",
            "software_version": "1.5.1",
            "uploader_callsign": "F4ICT-F4KLR",
            "uploader_position": "50.4977572,2.8616905555555556",
            "uploader_antenna": "Diamond X-200",
            "time_received": "2021-04-09T01:18:01.170006Z",
            "datetime": "2021-04-09T01:18:17.001000Z",
            "manufacturer": "Vaisala",
            "type": "RS41",
            "serial": "S2840432",
            "subtype": "RS41-SG",
            "frame": 8894,
            "lat": 51.05502,
            "lon": 2.5822,
            "alt": 949.41797,
            "temp": 2.1,
            "humidity": 63.8,
            "vel_v": -7.69568,
            "vel_h": 7.69487,
            "heading": 83.04947,
            "sats": 7, "batt": 2.6,
            "frequency": 404.801,
            "burst_timer": 28737,
            "snr": 19.3,
            "user-agent": "Amazon CloudFront",
            "position": "51.05502,2.5822",
            "upload_time_delta": -0.745924,
            "uploader_alt": 21.0
        }, {}
    )
