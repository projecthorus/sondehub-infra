# TODO
# add sns / sqs, AWS IoT actions
terraform {
  backend "s3" {
    bucket  = "sondehub-terraform"
    key     = "sondehub-main"
    region  = "us-east-1"
    profile = "sondes"
  }
}
provider "aws" {
  region  = "us-east-1"
  profile = "sondes"
}

locals {
  domain_name = "v2.sondehub.org"
}
data "aws_caller_identity" "current" {}

data "aws_iot_endpoint" "endpoint" {
  endpoint_type = "iot:Data-ATS"
}

resource "aws_iam_role" "IAMRole" {
  path                 = "/"
  name                 = "Cognito_sondesAuth_Role"
  assume_role_policy   = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {
            "Federated": "cognito-identity.amazonaws.com"
        },
        "Action": "sts:AssumeRoleWithWebIdentity",
        "Condition": {
            "StringEquals": {
                "cognito-identity.amazonaws.com:aud": "${aws_cognito_identity_pool.CognitoIdentityPool.id}"
            },
            "ForAnyValue:StringLike": {
                "cognito-identity.amazonaws.com:amr": "authenticated"
            }
        }
    }]
}
EOF
  max_session_duration = 3600
}

resource "aws_iam_role" "IAMRole2" {
  path                 = "/"
  name                 = "Cognito_sondesUnauth_Role"
  assume_role_policy   = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {
            "Federated": "cognito-identity.amazonaws.com"
        },
        "Action": "sts:AssumeRoleWithWebIdentity",
        "Condition": {
            "StringEquals": {
                "cognito-identity.amazonaws.com:aud": "${aws_cognito_identity_pool.CognitoIdentityPool.id}"
            },
            "ForAnyValue:StringLike": {
                "cognito-identity.amazonaws.com:amr": "unauthenticated"
            }
        }
    }]
}
EOF
  max_session_duration = 3600
}

resource "aws_iam_role" "IAMRole3" {
  path                 = "/service-role/"
  name                 = "CognitoAccessForAmazonES"
  assume_role_policy   = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {
            "Service": "es.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
    }]
}
EOF
  max_session_duration = 3600
}

resource "aws_iam_role" "IAMRole4" {
  path                 = "/service-role/"
  name                 = "iot-es"
  assume_role_policy   = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {
            "Service": "iot.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
    }]
}
EOF
  max_session_duration = 3600
}

resource "aws_iam_role" "IAMRole5" {
  path                 = "/service-role/"
  name                 = "sonde-api-to-iot-core-role-z9zes3f5"
  assume_role_policy   = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {
            "Service": "lambda.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
    }]
}
EOF
  max_session_duration = 3600
}



resource "aws_iam_role" "sign_socket" {
  name                 = "sign_socket"
  assume_role_policy   = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {
            "Service": "lambda.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
    }]
}
EOF
  max_session_duration = 3600
}

resource "aws_iam_role" "history" {
  name                 = "history"
  assume_role_policy   = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {
            "Service": "lambda.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
    }]
}
EOF
  max_session_duration = 3600
}

resource "aws_iam_service_linked_role" "IAMServiceLinkedRole" {
  aws_service_name = "es.amazonaws.com"
}

resource "aws_iam_service_linked_role" "IAMServiceLinkedRole3" {
  aws_service_name = "ops.apigateway.amazonaws.com"
  description      = "The Service Linked Role is used by Amazon API Gateway."
}

resource "aws_iam_policy" "IAMManagedPolicy" {
  name   = "AWSLambdaBasicExecutionRole-01b38736-6769-4407-9515-93d653f4db5f"
  path   = "/service-role/"
  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "logs:CreateLogGroup",
            "Resource": "arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": [
                "arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/*"
            ]
        }
    ]
}
EOF
}

resource "aws_sns_topic" "sonde_telem" {
  name            = "sonde-telem"
  delivery_policy = <<EOF
{
  "http": {
    "defaultHealthyRetryPolicy": {
      "minDelayTarget": 5,
      "maxDelayTarget": 30,
      "numRetries": 100,
      "numMaxDelayRetries": 0,
      "numNoDelayRetries": 3,
      "numMinDelayRetries": 0,
      "backoffFunction": "linear"
    },
    "disableSubscriptionOverrides": false
  }
}
EOF
}

resource "aws_iam_policy" "IAMManagedPolicy2" {
  name   = "aws-iot-role-es_795847808"
  path   = "/service-role/"
  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": {
        "Effect": "Allow",
        "Action": "es:ESHttpPut",
        "Resource": [
            "arn:aws:es:us-east-1:${data.aws_caller_identity.current.account_id}:domain/sondes-v2/*"
        ]
    }
}
EOF
}

resource "aws_iam_policy" "IAMManagedPolicy4" {
  name   = "AWSLambdaTracerAccessExecutionRole-56cd4e03-902a-4a40-9cd9-c9449709d80d"
  path   = "/service-role/"
  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": {
        "Effect": "Allow",
        "Action": [
            "xray:PutTraceSegments",
            "xray:PutTelemetryRecords"
        ],
        "Resource": [
            "*"
        ]
    }
}
EOF
}

resource "aws_iam_role_policy" "IAMPolicy" {
  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
               {
            "Effect": "Allow",
            "Action": "es:*",
            "Resource": "arn:aws:es:us-east-1:${data.aws_caller_identity.current.account_id}:domain/sondes-v2"
        },
        {
            "Effect": "Allow",
            "Action": "es:*",
            "Resource": "arn:aws:es:us-east-1:${data.aws_caller_identity.current.account_id}:domain/sondes-v2/*"
        }
    ]
}
EOF
  role   = aws_iam_role.IAMRole.name
}

resource "aws_iam_role_policy" "IAMPolicy2" {
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "mobileanalytics:PutEvents",
        "cognito-sync:*"
      ],
      "Resource": [
        "*"
      ]
    }
  ]
}
EOF
  role   = aws_iam_role.IAMRole2.name
}

resource "aws_iam_role_policy" "IAMPolicy3" {
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "mobileanalytics:PutEvents",
        "cognito-sync:*",
        "cognito-identity:*"
      ],
      "Resource": [
        "*"
      ]
    }
  ]
}
EOF
  role   = aws_iam_role.IAMRole.name
}

resource "aws_iam_role_policy" "IAMPolicy4" {
  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": "iot:*",
            "Resource": "*"
        },
        {
            "Sid": "VisualEditor1",
            "Effect": "Allow",
            "Action": "s3:*",
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": "sns:*",
            "Resource": "*"
        }
    ]
}
EOF
  role   = aws_iam_role.IAMRole5.name
}

resource "aws_iam_role_policy" "sign_socket" {
  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "iot:Connect",
            "Resource": "*"
        },
                {
            "Effect": "Allow",
            "Action": "iot:Subscribe",
            "Resource": "arn:aws:iot:us-east-1:${data.aws_caller_identity.current.account_id}:topicfilter/sondes/*"
        },
                {
            "Effect": "Allow",
            "Action": "iot:Receive",
            "Resource": "arn:aws:iot:us-east-1:${data.aws_caller_identity.current.account_id}:topic/sondes/*"
        }
    ]
}
EOF
  role   = aws_iam_role.sign_socket.name
}


resource "aws_iam_role_policy" "history" {
  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "s3:*",
            "Resource": "arn:aws:s3:::sondehub-open-data/*"
        },
        {
            "Effect": "Allow",
            "Action": "s3:*",
            "Resource": "arn:aws:s3:::sondehub-open-data"
        },
          {
            "Effect": "Allow",
            "Action": "logs:CreateLogGroup",
            "Resource": "arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": [
                "arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/*"
            ]
        },
                       {
            "Effect": "Allow",
            "Action": "es:*",
            "Resource": "arn:aws:es:us-east-1:${data.aws_caller_identity.current.account_id}:domain/sondes-v2"
        },
        {
            "Effect": "Allow",
            "Action": "es:*",
            "Resource": "arn:aws:es:us-east-1:${data.aws_caller_identity.current.account_id}:domain/sondes-v2/*"
        }
    ]
}
EOF
  role   = aws_iam_role.history.name
}

resource "aws_route53_zone" "Route53HostedZone" {
  name = "${local.domain_name}."
}

# resource "aws_route53_record" "Route53RecordSet" {
#   name = ""
#   type = "A"
#   ttl  = 300
#   records = [
#     "127.0.0.1"
#   ]
#   zone_id = aws_route53_zone.Route53HostedZone.zone_id
# }

resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.CertificateManagerCertificate.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = aws_route53_zone.Route53HostedZone.zone_id
}
resource "aws_acm_certificate_validation" "CertificateManagerCertificate" {
  certificate_arn         = aws_acm_certificate.CertificateManagerCertificate.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# resource "aws_route53_record" "Route53RecordSet5" {
#   name = "api"
#   type = "CNAME"
#   ttl  = 60
#   records = [
#     "${aws_apigatewayv2_domain_name.ApiGatewayV2DomainName.domain_name_configuration.0.target_domain_name}."
#   ]
#   zone_id = aws_route53_zone.Route53HostedZone.zone_id
# }

resource "aws_cognito_user_pool_domain" "main" {
  domain          = "auth.${local.domain_name}"
  user_pool_id    = aws_cognito_user_pool.CognitoUserPool.id
  certificate_arn = aws_acm_certificate_validation.CertificateManagerCertificate.certificate_arn
}

resource "aws_route53_record" "Route53RecordSet6" {
  name = "auth"
  type = "A"
  alias {
    name                   = "${aws_cognito_user_pool_domain.main.cloudfront_distribution_arn}."
    zone_id                = "Z2FDTNDATAQYW2"
    evaluate_target_health = false
  }
  zone_id = aws_route53_zone.Route53HostedZone.zone_id
}

resource "aws_route53_record" "Route53RecordSet7" {
  name = "es"
  type = "CNAME"
  ttl  = 300
  records = [
    aws_elasticsearch_domain.ElasticsearchDomain.endpoint
  ]
  zone_id = aws_route53_zone.Route53HostedZone.zone_id
}

data "archive_file" "api_to_iot" {
  type        = "zip"
  source_dir = "sonde-api-to-iot-core/"
  output_path = "${path.module}/build/sonde-api-to-iot-core.zip"
}

data "archive_file" "station_api_to_iot" {
  type        = "zip"
  source_file = "station-api-to-iot-core/lambda_function.py"
  output_path = "${path.module}/build/station-api-to-iot-core.zip"
}

data "archive_file" "query" {
  type        = "zip"
  source_file = "query/lambda_function.py"
  output_path = "${path.module}/build/query.zip"
}

data "archive_file" "history" {
  type        = "zip"
  source_file = "history/lambda_function.py"
  output_path = "${path.module}/build/history.zip"
}


data "archive_file" "sign_socket" {
  type        = "zip"
  source_file = "sign-websocket/lambda_function.py"
  output_path = "${path.module}/build/sign_socket.zip"
}

data "archive_file" "predictions" {
  type        = "zip"
  source_file = "predict/lambda_function.py"
  output_path = "${path.module}/build/predictions.zip"
}

resource "aws_lambda_function" "LambdaFunction" {
  function_name    = "sonde-api-to-iot-core"
  handler          = "lambda_function.lambda_handler"
  filename         = "${path.module}/build/sonde-api-to-iot-core.zip"
  source_code_hash = data.archive_file.api_to_iot.output_base64sha256
  publish          = true
  memory_size      = 256
  role             = aws_iam_role.IAMRole5.arn
  runtime          = "python3.7"
  timeout          = 30
  environment {
    variables = {
      "IOT_ENDPOINT" = data.aws_iot_endpoint.endpoint.endpoint_address
      "SNS_TOPIC" = aws_sns_topic.sonde_telem.arn
    }
  }
  layers = [
    "arn:aws:lambda:us-east-1:${data.aws_caller_identity.current.account_id}:layer:xray-python:1",
    "arn:aws:lambda:us-east-1:${data.aws_caller_identity.current.account_id}:layer:iot:3"
  ]
}

resource "aws_lambda_function" "station" {
  function_name    = "station-api-to-iot-core"
  handler          = "lambda_function.lambda_handler"
  filename         = "${path.module}/build/station-api-to-iot-core.zip"
  source_code_hash = data.archive_file.station_api_to_iot.output_base64sha256
  publish          = true
  memory_size      = 256
  role             = aws_iam_role.IAMRole5.arn
  runtime          = "python3.7"
  timeout          = 10
  environment {
    variables = {
      "IOT_ENDPOINT" = data.aws_iot_endpoint.endpoint.endpoint_address
    }
  }
  layers = [
    "arn:aws:lambda:us-east-1:${data.aws_caller_identity.current.account_id}:layer:xray-python:1",
    "arn:aws:lambda:us-east-1:${data.aws_caller_identity.current.account_id}:layer:iot:3"
  ]
}

resource "aws_lambda_function" "get_sondes" {
  function_name    = "query"
  handler          = "lambda_function.get_sondes"
  filename         = "${path.module}/build/query.zip"
  source_code_hash = data.archive_file.query.output_base64sha256
  publish          = true
  memory_size      = 256
  role             = aws_iam_role.IAMRole5.arn
  runtime          = "python3.7"
  timeout          = 30

  environment {
    variables = {
      "ES" = "es.${local.domain_name}"
    }
  }
  layers = [
    "arn:aws:lambda:us-east-1:${data.aws_caller_identity.current.account_id}:layer:xray-python:1",
    "arn:aws:lambda:us-east-1:${data.aws_caller_identity.current.account_id}:layer:iot:3"
  ]
}

resource "aws_lambda_function" "listeners" {
  function_name    = "listeners"
  handler          = "lambda_function.get_listeners"
  filename         = "${path.module}/build/query.zip"
  source_code_hash = data.archive_file.query.output_base64sha256
  publish          = true
  memory_size      = 256
  role             = aws_iam_role.IAMRole5.arn
  runtime          = "python3.7"
  timeout          = 30

  environment {
    variables = {
      "ES" = "es.${local.domain_name}"
    }
  }
  layers = [
    "arn:aws:lambda:us-east-1:${data.aws_caller_identity.current.account_id}:layer:xray-python:1",
    "arn:aws:lambda:us-east-1:${data.aws_caller_identity.current.account_id}:layer:iot:3"
  ]
}


resource "aws_lambda_function" "datanew" {
  function_name    = "datanew"
  handler          = "lambda_function.datanew"
  filename         = "${path.module}/build/query.zip"
  source_code_hash = data.archive_file.query.output_base64sha256
  publish          = true
  memory_size      = 1024
  role             = aws_iam_role.IAMRole5.arn
  runtime          = "python3.7"
  timeout          = 30

  environment {
    variables = {
      "ES" = "es.${local.domain_name}"
    }
  }
  layers = [
    "arn:aws:lambda:us-east-1:${data.aws_caller_identity.current.account_id}:layer:xray-python:1",
    "arn:aws:lambda:us-east-1:${data.aws_caller_identity.current.account_id}:layer:iot:3"
  ]
}

resource "aws_lambda_function" "predictions" {
  function_name    = "predictions"
  handler          = "lambda_function.predict"
  filename         = "${path.module}/build/predictions.zip"
  source_code_hash = data.archive_file.predictions.output_base64sha256
  publish          = true
  memory_size      = 256
  role             = aws_iam_role.IAMRole5.arn
  runtime          = "python3.7"
  timeout          = 30

  environment {
    variables = {
      "ES" = "es.${local.domain_name}"
    }
  }
  layers = [
    "arn:aws:lambda:us-east-1:${data.aws_caller_identity.current.account_id}:layer:xray-python:1",
    "arn:aws:lambda:us-east-1:${data.aws_caller_identity.current.account_id}:layer:iot:3"
  ]
}

resource "aws_lambda_function" "get_telem" {
  function_name    = "get_telem"
  handler          = "lambda_function.get_telem"
  filename         = "${path.module}/build/query.zip"
  source_code_hash = data.archive_file.query.output_base64sha256
  publish          = true
  memory_size      = 256
  role             = aws_iam_role.IAMRole5.arn
  runtime          = "python3.7"
  timeout          = 30

  environment {
    variables = {
      "ES" = "es.${local.domain_name}"
    }
  }
  layers = [
    "arn:aws:lambda:us-east-1:${data.aws_caller_identity.current.account_id}:layer:xray-python:1",
    "arn:aws:lambda:us-east-1:${data.aws_caller_identity.current.account_id}:layer:iot:3"
  ]
}

resource "aws_lambda_function" "get_listener_telemetry" {
  function_name    = "get_listener_telemetry"
  handler          = "lambda_function.get_listener_telemetry"
  filename         = "${path.module}/build/query.zip"
  source_code_hash = data.archive_file.query.output_base64sha256
  publish          = true
  memory_size      = 256
  role             = aws_iam_role.IAMRole5.arn
  runtime          = "python3.7"
  timeout          = 30
  layers = [
    "arn:aws:lambda:us-east-1:${data.aws_caller_identity.current.account_id}:layer:xray-python:1",
    "arn:aws:lambda:us-east-1:${data.aws_caller_identity.current.account_id}:layer:iot:3"
  ]
  environment {
    variables = {
      "ES" = "es.${local.domain_name}"
    }
  }
}

resource "aws_lambda_function" "sign_socket" {
  function_name    = "sign-websocket"
  handler          = "lambda_function.lambda_handler"
  filename         = "${path.module}/build/sign_socket.zip"
  source_code_hash = data.archive_file.sign_socket.output_base64sha256
  publish          = true
  memory_size      = 128
  role             = aws_iam_role.sign_socket.arn
  runtime          = "python3.7"
  timeout          = 10

  environment {
    variables = {
      "IOT_ENDPOINT" = data.aws_iot_endpoint.endpoint.endpoint_address
    }
  }
  layers = [
    "arn:aws:lambda:us-east-1:${data.aws_caller_identity.current.account_id}:layer:xray-python:1",
    "arn:aws:lambda:us-east-1:${data.aws_caller_identity.current.account_id}:layer:iot:3"
  ]
}

resource "aws_lambda_function" "history" {
  function_name    = "history"
  handler          = "lambda_function.history"
  filename         = "${path.module}/build/history.zip"
  source_code_hash = data.archive_file.history.output_base64sha256
  publish          = true
  memory_size      = 512
  role             = aws_iam_role.IAMRole5.arn
  runtime          = "python3.7"
  timeout          = 30
  environment {
    variables = {
      "ES" = "es.${local.domain_name}"
    }
  }

  layers = [
    "arn:aws:lambda:us-east-1:${data.aws_caller_identity.current.account_id}:layer:xray-python:1",
    "arn:aws:lambda:us-east-1:${data.aws_caller_identity.current.account_id}:layer:iot:3"
  ]
}

resource "aws_lambda_permission" "sign_socket" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sign_socket.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.ApiGatewayV2Api.id}/*/*/sondes/websocket"
}

resource "aws_lambda_permission" "history" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.history.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.ApiGatewayV2Api.id}/*/*/sonde/{serial}"
}

resource "aws_lambda_permission" "get_sondes" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_sondes.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.ApiGatewayV2Api.id}/*/*/sondes"
}

resource "aws_lambda_permission" "listeners" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.listeners.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.ApiGatewayV2Api.id}/*/*/listeners"
}

resource "aws_lambda_permission" "datanew" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.datanew.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.ApiGatewayV2Api.id}/*/*/datanew"
}

resource "aws_lambda_permission" "predictions" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.predictions.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.ApiGatewayV2Api.id}/*/*/predictions"
}


resource "aws_lambda_permission" "get_telem" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_telem.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.ApiGatewayV2Api.id}/*/*/sondes/telemetry"
}
resource "aws_lambda_permission" "get_listener_telemetry" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_listener_telemetry.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.ApiGatewayV2Api.id}/*/*/listeners/telemetry"
}

resource "aws_lambda_permission" "LambdaPermission2" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.LambdaFunction.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.ApiGatewayV2Api.id}/*/*/sondes/telemetry"
}

resource "aws_lambda_permission" "station" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.station.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.ApiGatewayV2Api.id}/*/*/listeners"
}

resource "aws_lambda_layer_version" "LambdaLayerVersion2" {
  compatible_runtimes = [
    "python3.8"
  ]
  layer_name       = "iot"
  s3_bucket        = "sondehub-lambda-layers"
  s3_key           = "iot.zip"
  source_code_hash = "sHyE9vXk+BzFphPe8evfiL79fcxsSEYVfpbTVi2IwH0="
}


resource "aws_lambda_layer_version" "LambdaLayerVersion4" {
  compatible_runtimes = [
    "python3.8"
  ]
  layer_name       = "xray-python"
  s3_bucket        = "sondehub-lambda-layers"
  s3_key           = "xray-python.zip"
  source_code_hash = "ta4o2brS2ZRAeWhZjqrm6MhOc3RlYNgkOuD4dxSonEc="
}

resource "aws_s3_bucket" "S3Bucket" {
  bucket = "sondehub-lambda-layers"
}

resource "aws_cloudwatch_log_group" "LogsLogGroup" {
  name = "/aws/lambda/sonde-api-to-iot-core"
}

resource "aws_apigatewayv2_api" "ApiGatewayV2Api" {
  name                         = "sondehub-v2"
  disable_execute_api_endpoint = true
  api_key_selection_expression = "$request.header.x-api-key"
  protocol_type                = "HTTP"
  route_selection_expression   = "$request.method $request.path"

  cors_configuration {
    allow_credentials = false
    allow_headers = [
      "*",
    ]
    allow_methods = [
      "*",
    ]
    allow_origins = [
      "*",
    ]
    expose_headers = []
    max_age        = 0
  }

}

resource "aws_apigatewayv2_stage" "ApiGatewayV2Stage" {
  name   = "$default"
  api_id = aws_apigatewayv2_api.ApiGatewayV2Api.id
  default_route_settings {
    detailed_metrics_enabled = false
  }
  auto_deploy = true
  lifecycle {
    ignore_changes = [deployment_id]
  }
}

resource "aws_apigatewayv2_stage" "ApiGatewayV2Stage2" {
  name          = "prod"
  api_id        = aws_apigatewayv2_api.ApiGatewayV2Api.id
  deployment_id = aws_apigatewayv2_deployment.ApiGatewayV2Deployment4.id
  default_route_settings {
    detailed_metrics_enabled = false
  }
}

resource "aws_apigatewayv2_deployment" "ApiGatewayV2Deployment3" {
  api_id = aws_apigatewayv2_api.ApiGatewayV2Api.id
}

resource "aws_apigatewayv2_deployment" "ApiGatewayV2Deployment4" {
  api_id = aws_apigatewayv2_api.ApiGatewayV2Api.id
}

resource "aws_apigatewayv2_route" "ApiGatewayV2Route" {
  api_id             = aws_apigatewayv2_api.ApiGatewayV2Api.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "PUT /sondes/telemetry"
  target             = "integrations/${aws_apigatewayv2_integration.ApiGatewayV2Integration.id}"
}

resource "aws_apigatewayv2_route" "stations" {
  api_id             = aws_apigatewayv2_api.ApiGatewayV2Api.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "PUT /listeners"
  target             = "integrations/${aws_apigatewayv2_integration.stations.id}"
}


resource "aws_apigatewayv2_route" "sign_socket" {
  api_id             = aws_apigatewayv2_api.ApiGatewayV2Api.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /sondes/websocket"
  target             = "integrations/${aws_apigatewayv2_integration.sign_socket.id}"
}
resource "aws_apigatewayv2_route" "history" {
  api_id             = aws_apigatewayv2_api.ApiGatewayV2Api.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /sonde/{serial}"
  target             = "integrations/${aws_apigatewayv2_integration.history.id}"
}

resource "aws_apigatewayv2_route" "get_sondes" {
  api_id             = aws_apigatewayv2_api.ApiGatewayV2Api.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /sondes"
  target             = "integrations/${aws_apigatewayv2_integration.get_sondes.id}"
}

resource "aws_apigatewayv2_route" "listeners" {
  api_id             = aws_apigatewayv2_api.ApiGatewayV2Api.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /listeners"
  target             = "integrations/${aws_apigatewayv2_integration.listeners.id}"
}

resource "aws_apigatewayv2_route" "datanew" {
  api_id             = aws_apigatewayv2_api.ApiGatewayV2Api.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /datanew"
  target             = "integrations/${aws_apigatewayv2_integration.datanew.id}"
}

resource "aws_apigatewayv2_route" "predictions" {
  api_id             = aws_apigatewayv2_api.ApiGatewayV2Api.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /predictions"
  target             = "integrations/${aws_apigatewayv2_integration.predictions.id}"
}

resource "aws_apigatewayv2_route" "get_telem" {
  api_id             = aws_apigatewayv2_api.ApiGatewayV2Api.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /sondes/telemetry"
  target             = "integrations/${aws_apigatewayv2_integration.get_telem.id}"
}

resource "aws_apigatewayv2_route" "get_listener_telemetry" {
  api_id             = aws_apigatewayv2_api.ApiGatewayV2Api.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /listeners/telemetry"
  target             = "integrations/${aws_apigatewayv2_integration.get_listener_telemetry.id}"
}

resource "aws_apigatewayv2_integration" "sign_socket" {
  api_id                 = aws_apigatewayv2_api.ApiGatewayV2Api.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.sign_socket.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "history" {
  api_id                 = aws_apigatewayv2_api.ApiGatewayV2Api.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.history.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "get_sondes" {
  api_id                 = aws_apigatewayv2_api.ApiGatewayV2Api.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_sondes.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "listeners" {
  api_id                 = aws_apigatewayv2_api.ApiGatewayV2Api.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.listeners.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "datanew" {
  api_id                 = aws_apigatewayv2_api.ApiGatewayV2Api.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.datanew.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "predictions" {
  api_id                 = aws_apigatewayv2_api.ApiGatewayV2Api.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.predictions.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "get_telem" {
  api_id                 = aws_apigatewayv2_api.ApiGatewayV2Api.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_telem.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "get_listener_telemetry" {
  api_id                 = aws_apigatewayv2_api.ApiGatewayV2Api.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_listener_telemetry.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "ApiGatewayV2Integration" {
  api_id                 = aws_apigatewayv2_api.ApiGatewayV2Api.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.LambdaFunction.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "stations" {
  api_id                 = aws_apigatewayv2_api.ApiGatewayV2Api.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.station.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_api_mapping" "ApiGatewayV2ApiMapping" {
  api_id          = aws_apigatewayv2_api.ApiGatewayV2Api.id
  domain_name     = aws_apigatewayv2_domain_name.ApiGatewayV2DomainName.id
  stage           = "$default"
  api_mapping_key = ""
}

resource "aws_apigatewayv2_domain_name" "ApiGatewayV2DomainName" {
  domain_name = "api-raw.${local.domain_name}"
  domain_name_configuration {
    certificate_arn = aws_acm_certificate_validation.CertificateManagerCertificate.certificate_arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }
}

resource "aws_acm_certificate" "CertificateManagerCertificate" {
  domain_name = local.domain_name
  subject_alternative_names = [
    "*.${local.domain_name}"
  ]
  validation_method = "DNS"
}

resource "aws_elasticsearch_domain" "ElasticsearchDomain" {
  domain_name           = "sondes-v2"
  elasticsearch_version = "7.9"
  cluster_config {
    dedicated_master_count   = 3
    dedicated_master_enabled = false
    dedicated_master_type    = "t3.small.elasticsearch"
    instance_count           = 1
    instance_type            = "r5.xlarge.elasticsearch"
    zone_awareness_enabled   = false
  }
  cognito_options {
    enabled          = true
    identity_pool_id = aws_cognito_identity_pool.CognitoIdentityPool.id
    role_arn         = aws_iam_role.IAMRole3.arn
    user_pool_id     = aws_cognito_user_pool.CognitoUserPool.id
  }

  access_policies = <<EOF
    {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "*"
            },
            "Action": "es:*",
            "Resource": "arn:aws:es:us-east-1:${data.aws_caller_identity.current.account_id}:domain/sondes-v2/*"
        }
    ]
}
EOF
  encrypt_at_rest {
    enabled    = true
    kms_key_id = data.aws_kms_key.es.arn
  }
  node_to_node_encryption {
    enabled = true
  }
  advanced_options = {
    "rest.action.multi.allow_explicit_index" = "true"
  }
  ebs_options {
    ebs_enabled = true
    volume_type = "gp2"
    volume_size = 250
  }
  log_publishing_options {
    cloudwatch_log_group_arn = "arn:aws:logs:us-east-1:143841941773:log-group:/aws/aes/domains/sondes-v2/application-logs"
    enabled                  = true
    log_type                 = "ES_APPLICATION_LOGS"
  }
}
data "aws_kms_key" "es" {
  key_id = "alias/aws/es"
}

resource "aws_cognito_identity_pool" "CognitoIdentityPool" {
  identity_pool_name               = "sondes"
  allow_unauthenticated_identities = true
  supported_login_providers = {
    "accounts.google.com" = "575970424139-vkk7scicbdd1igj04riqjh2bbs0oa6vj.apps.googleusercontent.com"
  }
  cognito_identity_providers {
    client_id               = aws_cognito_user_pool_client.CognitoUserPoolClient.id
    provider_name           = aws_cognito_user_pool.CognitoUserPool.endpoint
    server_side_token_check = false
  }
}

resource "aws_cognito_identity_pool_roles_attachment" "CognitoIdentityPoolRoleAttachment" {
  identity_pool_id = aws_cognito_identity_pool.CognitoIdentityPool.id
  roles = {
    authenticated   = aws_iam_role.IAMRole.arn
    unauthenticated = aws_iam_role.IAMRole2.arn
  }
  role_mapping {
    ambiguous_role_resolution = "AuthenticatedRole"
    identity_provider         = "cognito-idp.us-east-1.amazonaws.com/us-east-1_G4H7NMniM:5sngha3l291nb4784iid5hli48"
    type                      = "Token"
  }
}

resource "aws_cognito_user_pool" "CognitoUserPool" {
  name = "sondes"
  password_policy {
    temporary_password_validity_days = 7
    minimum_length                   = 8
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = true
    require_uppercase                = true
  }

  schema {
    attribute_data_type      = "String"
    developer_only_attribute = false
    mutable                  = true
    name                     = "email"
    string_attribute_constraints {
      max_length = "2048"
      min_length = "0"
    }
    required = true
  }
  username_configuration {
    case_sensitive = false
  }

  auto_verified_attributes = [
    "email"
  ]
  alias_attributes = [
    "email",
    "preferred_username"
  ]
  sms_verification_message   = "Your verification code is {####}. "
  email_verification_message = "Your verification code is {####}. "
  email_verification_subject = "Your verification code"
  sms_authentication_message = "Your authentication code is {####}. "
  mfa_configuration          = "OFF"
  device_configuration {
    challenge_required_on_new_device      = false
    device_only_remembered_on_user_prompt = false
  }
  email_configuration {

  }
  admin_create_user_config {
    allow_admin_create_user_only = false
    invite_message_template {
      email_message = "Your username is {username} and temporary password is {####}. "
      email_subject = "Your temporary password"
      sms_message   = "Your username is {username} and temporary password is {####}. "
    }
  }
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }
}

resource "aws_cognito_user_pool_client" "CognitoUserPoolClient" {
  user_pool_id                         = aws_cognito_user_pool.CognitoUserPool.id
  name                                 = "AWSElasticsearch-sondes-v2-us-east-1-hiwdpmnjbuckpbwfhhx65mweee"
  refresh_token_validity               = 30
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes                 = ["email", "openid", "phone", "profile"]
  callback_urls                        = ["https://es.${local.domain_name}/_plugin/kibana/app/kibana"]
  logout_urls                          = ["https://es.${local.domain_name}/_plugin/kibana/app/kibana"]
  supported_identity_providers         = ["COGNITO", "Google"]
  explicit_auth_flows                  = ["ALLOW_CUSTOM_AUTH", "ALLOW_REFRESH_TOKEN_AUTH", "ALLOW_USER_SRP_AUTH"]
}