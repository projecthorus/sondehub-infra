import boto3
import time
import uuid
import urllib.parse
import hmac, datetime, hashlib
import os

def lambda_handler(event, context):
 
    return {"statusCode": 200, "body": "wss://ws-reader.v2.sondehub.org/"}

if __name__ == "__main__":
    print(lambda_handler({}, {}))