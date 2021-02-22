import boto3
import json
import os
from datetime import datetime, timedelta
import threading
from queue import Queue
import queue
from botocore import UNSIGNED
from botocore.config import Config

S3_BUCKET = "sondehub-open-data"

class Downloader(threading.Thread): # Stolen from the SDK, if I wasn't lazy I'd made a build chain for this lambda so we can reuse the code in both projects
    def __init__(
        self, tasks_to_accomplish, tasks_that_are_done, debug=False, *args, **kwargs
    ):
        self.tasks_to_accomplish = tasks_to_accomplish
        self.tasks_that_are_done = tasks_that_are_done
        self.debug = debug
        super().__init__(*args, **kwargs)

    def run(self):
        s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))
        while True:
            try:
                task = self.tasks_to_accomplish.get_nowait()
            except queue.Empty:
                return
            data = s3.get_object(Bucket=task[0], Key=task[1])
            response = json.loads(data["Body"].read())
            if self.debug:
                print(response)
            self.tasks_that_are_done.put(response)
            self.tasks_to_accomplish.task_done()


def download(serial):
    prefix_filter = f"serial-hashed/{serial}/"

    s3 = boto3.resource("s3", config=Config(signature_version=UNSIGNED))
    bucket = s3.Bucket(S3_BUCKET)
    data = []

    number_of_processes = 200
    tasks_to_accomplish = Queue()
    tasks_that_are_done = Queue()

    for s3_object in bucket.objects.filter(Prefix=prefix_filter):
        tasks_to_accomplish.put((s3_object.bucket_name, s3_object.key))

    for _ in range(number_of_processes):
        Downloader(tasks_to_accomplish, tasks_that_are_done, False).start()
    tasks_to_accomplish.join()

    while not tasks_that_are_done.empty():
        data.append(tasks_that_are_done.get())

    return data

def history(event, context):
    radiosondes = download(serial=event["pathParameters"]["serial"])
    return json.dumps(radiosondes)

if __name__ == "__main__":
    # print(get_sondes({"queryStringParameters":{"lat":"-28.22717","lon":"153.82996","distance":"50000"}}, {}))
    print(
        history(
            {"pathParameters": {"serial": "R2450480"}}, {}
        )
    )
