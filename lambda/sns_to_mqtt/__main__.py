from . import *
import uuid

class fakeContext:
    def __init__(self):
        self.log_stream_name = str(uuid.uuid4())
# test event
###########
if __name__ == "__main__":
    demo_event = {
        "Records": [
            {
                "messageId": "262d4090-e23b-4907-b677-3c94334dc899",
                "receiptHandle": "AQEBL1FXHS4m+Om59KZH9ayxC5VBqDEDh6DgXUZuBhV2uQJS312bhOTpLvptuCCIWaeLkfHU+7NajqV2kTVhnz5lehE/zfQ8OU1jqqm+cHxyul99MxA7K7+C+ww2Ri9KSbgaAgqvZzcLbwpW8rP0MNhrBcIQAE5Pz1urfTZKx1RVnv/XQHbR2ARPwocOzk2yEexa0y2f7FedS4F10gju8Ypp0Zr4DSRb1zUkES3QJGiSJakaO1QJT5npRySjAd0CUSPXw7IDTejolfGkItQG5eMRx0enELTUDv8LPsHJkr7ha3DHNfbvxTtdk406nWFn8U8DW515emp7+Y+AD469OnceIMdVC62GHwrpMkedXzLEH0C8TOXHQ+WuRkhR1dauwKqO",
                "Sns": {'Type': 'Notification', 'MessageId': '65147554-e06d-5324-a87d-2da107fea807', 'TopicArn': 'arn:aws:sns:us-east-1:143841941773:sonde-telem', 'Message': '{"software_name":"radiosonde_auto_rx","software_version":"1.5.1","uploader_callsign":"BIOWL1","uploader_position":"52.014417,8.47351","uploader_antenna":"SirioCX395","time_received":"2021-04-18T07:52:37.196266Z","datetime":"2021-04-18T07:52:53.001000Z","manufacturer":"Vaisala","type":"RS41","serial":"meowmeowtest","subtype":"RS41-SGP","frame":12781,"lat":50.65064,"lon":6.60805,"alt":2954.44289,"temp":-9.3,"humidity":75.4,"pressure":709.79,"vel_v":-2.85326,"vel_h":8.53055,"heading":236.0122,"sats":9,"batt":2.7,"frequency":405.3,"burst_timer":25423,"snr":12.5,"user-agent":"Amazon CloudFront","position":"50.65064,6.60805","upload_time_delta":-0.713689,"uploader_alt":340}', 'Timestamp': '2021-04-18T07:52:51.776Z', 'SignatureVersion': '1', 'Signature': 'qXuYwDAGPYYLjKXfDtF69AWKDEhhz9MXlqxO2nBwJ/dgOqNSUZtDPqOYSuge3jVCoTSRY5qGw38gg2G+JnEbJd8SVvp9GRsFre8MKWu8T0obq3rj8S0YAh7dTqi4EILIMmi2KziasCDQlrVuZvCSgPnC+hYF3GByI626QW6m3a4E2igclvbE+O6x6qvVDKwmf/eh+8LRiH1PCrEckiXthnr+qOCiTcstyZoOqMOShJBun9k0DK07+Yf1tYDPSHnqZSIaOvAMSjIKKXfGCkel3SWieO7Zgk7xQuo9Z1bcV8Miu4uEvge4G9HKU3S41zaVcQjYvEhQLxxgd1x3HxXImA==', 'SigningCertURL': 'https://sns.us-east-1.amazonaws.com/SimpleNotificationService-010a507c1833636cd94bdb98bd93083a.pem', 'UnsubscribeURL': 'https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-east-1:143841941773:sonde-telem:1a52ac41-6e17-43da-bfb6-114577c94ca6'},
                "attributes": {
                    "ApproximateReceiveCount": "2",
                    "SentTimestamp": "1618732371814",
                    "SenderId": "AIDAIT2UOQQY3AUEKVGXU",
                    "ApproximateFirstReceiveTimestamp": "1618732640317"
                },
                "messageAttributes": {},
                "md5OfMessageAttributes": None,
                "md5OfBody": "a0191fc5ea3705340c088e457c31095b",
                "eventSource": "aws:sqs",
                "eventSourceARN": "arn:aws:sqs:us-east-1:143841941773:to-elk",
                "awsRegion": "us-east-1"
            }
        ]
    }
    print(lambda_handler(demo_event, fakeContext()))

    
