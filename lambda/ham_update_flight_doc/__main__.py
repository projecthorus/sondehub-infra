from . import *
# payload = {
#     "version": "2.0",
#     "routeKey": "PUT /amateur/flightdoc",
#     "rawPath": "/amateur/flightdoc",
#     "rawQueryString": "",
#     "headers": {
#         "accept": "*/*",
#         "accept-encoding": "gzip, deflate, br",
#         "accept-language": "en-AU,en;q=0.9",
#         "authorization": "AWS4-HMAC-SHA256 Credential=ASIASC7NF3EG2IN32V5U/20220510/us-east-1/execute-api/aws4_request, SignedHeaders=host;x-amz-content-sha256;x-amz-date;x-amz-security-token;x-amz-user-agent, Signature=2c79b43997baee65869b98bbf8525116a297d57d90af1f311b5c1ff0e046cab0",
#         "content-length": "109",
#         "content-type": "application/json",
#         "host": "api-raw.v2.sondehub.org",
#         "origin": "http://localhost:8000",
#         "referer": "http://localhost:8000/",
#         "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15",
#         "x-amz-content-sha256": "5cdaa82af662f6efdff22bc28a9ce534a4250025378f30f7b917506d31cbec90",
#         "x-amz-date": "20220510T233932Z",
#         "x-amz-security-token": "IQoJb3JpZ2luX2VjEEgaCXVzLWVhc3QtMSJIMEYCIQC1dWVTNpEB0saU5TPR9NHVmOdiBK1QfjMB1LrPZsea+AIhAIuhvNxDNF/gUaNrnmgK2de45dogn8+1C5HhEpqpKHqBKsQECCEQARoMMTQzODQxOTQxNzczIgzIMKmrFJy94ru7nrwqoQRnvyF9anCZpsqJbtc8X2aErXQvZwrKClPq26KpnHot4alk8k4WzOHjFYA1GOPDpbAPe8jpTKoNpzcU7twpKDk6znA+fo3bSnkhAqAyackmag7Tff4w5bABgysWmHafHrZBo4TIyihlRSmHSZNUo7NwFajOKg5wiHSrneF719Qxl1hcbqp5FuxUG1xWc8ySUOFarQ+gxtm1yGz33WMYqjkND1R5wANH3ii4Wz39Xd4FR5IJgm5nAdyaKVM536tW/KZOOtbyGPlMyyGjKNZYV0PDtWclHaBEPwSgCI4m+l5WRga2/WQuRtkTFAQXSn45aGcT7nUNflixbyD0tsHuHILFVOr64MVliumnTf7v60FJjUJqyTLYlG4hcSG+U+FWxFnBcWxPklILzx3QtSRj0gOCIV8rll5i6APq9vngHu3QBC9V96w06Fgz21jmyv2KF4/+lYTSR4d5DwF44+OttE9vtoibV8i7nZCZcNLwzb3F9qMyAmnJL2I2ZjcL8JeJyd9fz9IBiT1T2E/vmD1yfZt5gGN3/N+aSwj+w30CChUt8bhdpTVJqUtPhnLYdT3rOAez84HWvOmMIrZakCSy+ZRixLP6JCjmko2uQvKF3ohUeVGs97Z4d1cyJKaGYNxq7Jm48xy8oa5zsFN6b2up0fpRa7UqvFsiAMYq7C3SZKHiry67GO8ESa0zJkjke5g/SGNUf1O6IrmyuDScg/r2SjF9zzCM7uuTBjqEAjkBXGngIs6QyM2CUNEKAfGZ+MSM5D/da4EdnKIN+YJsu4KHYTepXDGtCpXuXmsI0fZkN7lxQPBYxtRnRzngph0SZaXq8cxLY/PBPievd4oQ8dnGX9Gy9lPLyq360igqlpxXAAke8C2CORr+y29pO6M8lFg7ds47Y5TXQ8wyfdUQAtXkBqklqHNEDMNJrZPFg/dJqSEGxxT/1GYNTdUKupGkNw0fHAv9XoBeewPsXoulOk4HlyiaKeEpZZWDsclpjNHtEYaASR0KzlWJ/KYPTkFaGpb8OzMg/KKL3Qvg8t8drEy5LZPhWNIOvOnKYaf+6V0nL62yS03YMIa07dADPwUTSHgA",
#         "x-amz-user-agent": "aws-sdk-js/2.1130.0",
#         "x-amzn-trace-id": "Root=1-627af7b4-5966222c69fc1dcb6a0d98e0",
#         "x-forwarded-for": "14.203.163.173",
#         "x-forwarded-port": "443",
#         "x-forwarded-proto": "https"
#     },
#     "requestContext": {
#         "accountId": "143841941773",
#         "apiId": "r03szwwq41",
#         "authorizer": {
#             "iam": {
#                 "accessKey": "ASIASC7NF3EG2IN32V5U",
#                 "accountId": "143841941773",
#                 "callerId": "AROASC7NF3EGZURC7BJTC:CognitoIdentityCredentials",
#                 "cognitoIdentity": {
#                     "amr": [
#                         "authenticated",
#                         "cognito-idp.us-east-1.amazonaws.com/us-east-1_G4H7NMniM",
#                         "cognito-idp.us-east-1.amazonaws.com/us-east-1_G4H7NMniM:CognitoSignIn:61f3c171-39f9-474b-9900-9953b755b474"
#                     ],
#                     "identityId": "us-east-1:54e08cdd-84df-42b3-ab16-e568ef118e8c",
#                     "identityPoolId": "us-east-1:55e43eac-9626-43e1-a7d2-bbc57f5f5aa9"
#                 },
#                 "principalOrgId": None,
#                 "userArn": "arn:aws:sts::143841941773:assumed-role/Cognito_sondesAuth_Role/CognitoIdentityCredentials",
#                 "userId": "AROASC7NF3EGZURC7BJTC:CognitoIdentityCredentials"
#             }
#         },
#         "domainName": "api-raw.v2.sondehub.org",
#         "domainPrefix": "api-raw",
#         "http": {
#             "method": "PUT",
#             "path": "/amateur/flightdoc",
#             "protocol": "HTTP/1.1",
#             "sourceIp": "14.203.163.173",
#             "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15"
#         },
#         "requestId": "R7ukRiWYIAMEJ2g=",
#         "routeKey": "PUT /amateur/flightdoc",
#         "stage": "$default",
#         "time": "10/May/2022:23:39:32 +0000",
#         "timeEpoch": 1652225972793
#     },
#     "body": "{\"payload_callsign\":\"4FSKTEST\",\"float_expected\":false,\"peak_altitude\":30000,\"descent_rate\":5,\"ascent_rate\":5}",
#     "isBase64Encoded": False
# }
payload = {
    "version": "2.0",
    "routeKey": "PUT /amateur/flightdoc",
    "rawPath": "/amateur/flightdoc",
    "rawQueryString": "",
    "headers": {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-AU,en;q=0.9",
        "authorization": "AWS4-HMAC-SHA256 Credential=ASIASC7NF3EG2IN32V5U/20220510/us-east-1/execute-api/aws4_request, SignedHeaders=host;x-amz-content-sha256;x-amz-date;x-amz-security-token;x-amz-user-agent, Signature=2c79b43997baee65869b98bbf8525116a297d57d90af1f311b5c1ff0e046cab0",
        "content-length": "109",
        "content-type": "application/json",
        "host": "api-raw.v2.sondehub.org",
        "origin": "http://localhost:8000",
        "referer": "http://localhost:8000/",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15",
        "x-amz-content-sha256": "5cdaa82af662f6efdff22bc28a9ce534a4250025378f30f7b917506d31cbec90",
        "x-amz-date": "20220510T233932Z",
        "x-amz-security-token": "IQoJb3JpZ2luX2VjEEgaCXVzLWVhc3QtMSJIMEYCIQC1dWVTNpEB0saU5TPR9NHVmOdiBK1QfjMB1LrPZsea+AIhAIuhvNxDNF/gUaNrnmgK2de45dogn8+1C5HhEpqpKHqBKsQECCEQARoMMTQzODQxOTQxNzczIgzIMKmrFJy94ru7nrwqoQRnvyF9anCZpsqJbtc8X2aErXQvZwrKClPq26KpnHot4alk8k4WzOHjFYA1GOPDpbAPe8jpTKoNpzcU7twpKDk6znA+fo3bSnkhAqAyackmag7Tff4w5bABgysWmHafHrZBo4TIyihlRSmHSZNUo7NwFajOKg5wiHSrneF719Qxl1hcbqp5FuxUG1xWc8ySUOFarQ+gxtm1yGz33WMYqjkND1R5wANH3ii4Wz39Xd4FR5IJgm5nAdyaKVM536tW/KZOOtbyGPlMyyGjKNZYV0PDtWclHaBEPwSgCI4m+l5WRga2/WQuRtkTFAQXSn45aGcT7nUNflixbyD0tsHuHILFVOr64MVliumnTf7v60FJjUJqyTLYlG4hcSG+U+FWxFnBcWxPklILzx3QtSRj0gOCIV8rll5i6APq9vngHu3QBC9V96w06Fgz21jmyv2KF4/+lYTSR4d5DwF44+OttE9vtoibV8i7nZCZcNLwzb3F9qMyAmnJL2I2ZjcL8JeJyd9fz9IBiT1T2E/vmD1yfZt5gGN3/N+aSwj+w30CChUt8bhdpTVJqUtPhnLYdT3rOAez84HWvOmMIrZakCSy+ZRixLP6JCjmko2uQvKF3ohUeVGs97Z4d1cyJKaGYNxq7Jm48xy8oa5zsFN6b2up0fpRa7UqvFsiAMYq7C3SZKHiry67GO8ESa0zJkjke5g/SGNUf1O6IrmyuDScg/r2SjF9zzCM7uuTBjqEAjkBXGngIs6QyM2CUNEKAfGZ+MSM5D/da4EdnKIN+YJsu4KHYTepXDGtCpXuXmsI0fZkN7lxQPBYxtRnRzngph0SZaXq8cxLY/PBPievd4oQ8dnGX9Gy9lPLyq360igqlpxXAAke8C2CORr+y29pO6M8lFg7ds47Y5TXQ8wyfdUQAtXkBqklqHNEDMNJrZPFg/dJqSEGxxT/1GYNTdUKupGkNw0fHAv9XoBeewPsXoulOk4HlyiaKeEpZZWDsclpjNHtEYaASR0KzlWJ/KYPTkFaGpb8OzMg/KKL3Qvg8t8drEy5LZPhWNIOvOnKYaf+6V0nL62yS03YMIa07dADPwUTSHgA",
        "x-amz-user-agent": "aws-sdk-js/2.1130.0",
        "x-amzn-trace-id": "Root=1-627af7b4-5966222c69fc1dcb6a0d98e0",
        "x-forwarded-for": "14.203.163.173",
        "x-forwarded-port": "443",
        "x-forwarded-proto": "https"
    },
    "requestContext": {
        "accountId": "143841941773",
        "apiId": "r03szwwq41",
        "authorizer": {
            "iam": {
                "accessKey": "ASIASC7NF3EG2IN32V5U",
                "accountId": "143841941773",
                "callerId": "AROASC7NF3EGZURC7BJTC:CognitoIdentityCredentials",
                "cognitoIdentity": {
                    "amr": [
                        "authenticated",
                        "cognito-idp.us-east-1.amazonaws.com/us-east-1_G4H7NMniM",
                        "cognito-idp.us-east-1.amazonaws.com/us-east-1_G4H7NMniM:CognitoSignIn:61f3c171-39f9-474b-9900-9953b755b474"
                    ],
                    "identityId": "us-east-1:54e08cdd-84df-42b3-ab16-e568ef118e8c",
                    "identityPoolId": "us-east-1:55e43eac-9626-43e1-a7d2-bbc57f5f5aa9"
                },
                "principalOrgId": None,
                "userArn": "arn:aws:sts::143841941773:assumed-role/Cognito_sondesAuth_Role/CognitoIdentityCredentials",
                "userId": "AROASC7NF3EGZURC7BJTC:CognitoIdentityCredentials"
            }
        },
        "domainName": "api-raw.v2.sondehub.org",
        "domainPrefix": "api-raw",
        "http": {
            "method": "GET",
            "path": "/amateur/flightdoc",
            "protocol": "HTTP/1.1",
            "sourceIp": "14.203.163.173",
            "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15"
        },
        "requestId": "R7ukRiWYIAMEJ2g=",
        "routeKey": "PUT /amateur/flightdoc",
        "stage": "$default",
        "time": "10/May/2022:23:39:32 +0000",
        "timeEpoch": 1652225972793
    },
    "pathParameters" : {
        "payload_callsign" : "HORUS-V2"
    },
    "body": "",
    "isBase64Encoded": False
}
print(query(payload, {}))