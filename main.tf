# TODO
# add sns / sqs
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


resource "aws_iam_role_policy" "IAMPolicy4" {
  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
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





resource "aws_lambda_function" "get_sondes" {
  function_name    = "query"
  handler          = "lambda_function.get_sondes"
  filename         = "${path.module}/build/query.zip"
  source_code_hash = data.archive_file.query.output_base64sha256
  publish          = true
  memory_size      = 256
  role             = aws_iam_role.IAMRole5.arn
  runtime          = "python3.9"
  timeout          = 30
  architectures    = ["arm64"]
  environment {
    variables = {
      "ES" = "es.${local.domain_name}"
    }
  }
}




resource "aws_lambda_function" "predictions" {
  function_name    = "predictions"
  handler          = "lambda_function.predict"
  filename         = "${path.module}/build/predictions.zip"
  source_code_hash = data.archive_file.predictions.output_base64sha256
  publish          = true
  memory_size      = 128
  role             = aws_iam_role.IAMRole5.arn
  runtime          = "python3.9"
  timeout          = 30
  architectures    = ["arm64"]
  environment {
    variables = {
      "ES" = "es.${local.domain_name}"
    }
  }
}

resource "aws_lambda_function" "get_telem" {
  function_name    = "get_telem"
  handler          = "lambda_function.get_telem"
  filename         = "${path.module}/build/query.zip"
  source_code_hash = data.archive_file.query.output_base64sha256
  publish          = true
  memory_size      = 256
  role             = aws_iam_role.IAMRole5.arn
  runtime          = "python3.9"
  timeout          = 30
  architectures    = ["arm64"]
  environment {
    variables = {
      "ES" = "es.${local.domain_name}"
    }
  }
}

resource "aws_lambda_function" "get_sites" {
  function_name    = "get_sites"
  handler          = "lambda_function.get_sites"
  filename         = "${path.module}/build/query.zip"
  source_code_hash = data.archive_file.query.output_base64sha256
  publish          = true
  memory_size      = 256
  role             = aws_iam_role.IAMRole5.arn
  runtime          = "python3.9"
  timeout          = 30
  architectures    = ["arm64"]
  environment {
    variables = {
      "ES" = "es.${local.domain_name}"
    }
  }
}

resource "aws_lambda_function" "get_listener_telemetry" {
  function_name    = "get_listener_telemetry"
  handler          = "lambda_function.get_listener_telemetry"
  filename         = "${path.module}/build/query.zip"
  source_code_hash = data.archive_file.query.output_base64sha256
  publish          = true
  memory_size      = 256
  role             = aws_iam_role.IAMRole5.arn
  runtime          = "python3.9"
  timeout          = 30
  architectures    = ["arm64"]
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
  runtime          = "python3.9"
  timeout          = 10
  architectures    = ["arm64"]
}

resource "aws_lambda_function" "history" {
  function_name                  = "history"
  handler                        = "lambda_function.history"
  filename                       = "${path.module}/build/history.zip"
  source_code_hash               = data.archive_file.history.output_base64sha256
  publish                        = true
  memory_size                    = 512
  role                           = aws_iam_role.IAMRole5.arn
  runtime                        = "python3.9"
  timeout                        = 30
  reserved_concurrent_executions = 4
  architectures                  = ["arm64"]
  environment {
    variables = {
      "ES" = "es.${local.domain_name}"
    }
  }


}

resource "aws_lambda_permission" "sign_socket" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sign_socket.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/sondes/websocket"
}

resource "aws_lambda_permission" "history" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.history.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/sonde/{serial}"
}

resource "aws_lambda_permission" "get_sondes" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_sondes.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/sondes"
}

resource "aws_lambda_permission" "get_sites" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_sites.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/sites"
}


resource "aws_lambda_permission" "predictions" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.predictions.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/predictions"
}


resource "aws_lambda_permission" "get_telem" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_telem.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/sondes/telemetry"
}
resource "aws_lambda_permission" "get_listener_telemetry" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_listener_telemetry.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/listeners/telemetry"
}













resource "aws_apigatewayv2_route" "sign_socket" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /sondes/websocket"
  target             = "integrations/${aws_apigatewayv2_integration.sign_socket.id}"
}
resource "aws_apigatewayv2_route" "history" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /sonde/{serial}"
  target             = "integrations/${aws_apigatewayv2_integration.history.id}"
}

resource "aws_apigatewayv2_route" "get_sondes" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /sondes"
  target             = "integrations/${aws_apigatewayv2_integration.get_sondes.id}"
}

resource "aws_apigatewayv2_route" "get_sites" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /sites"
  target             = "integrations/${aws_apigatewayv2_integration.get_sites.id}"
}



resource "aws_apigatewayv2_route" "predictions" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /predictions"
  target             = "integrations/${aws_apigatewayv2_integration.predictions.id}"
}

resource "aws_apigatewayv2_route" "get_telem" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /sondes/telemetry"
  target             = "integrations/${aws_apigatewayv2_integration.get_telem.id}"
}

resource "aws_apigatewayv2_route" "get_listener_telemetry" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /listeners/telemetry"
  target             = "integrations/${aws_apigatewayv2_integration.get_listener_telemetry.id}"
}

resource "aws_apigatewayv2_integration" "sign_socket" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.sign_socket.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "history" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.history.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "get_sondes" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_sondes.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "get_sites" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_sites.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}


resource "aws_apigatewayv2_integration" "predictions" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.predictions.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "get_telem" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_telem.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "get_listener_telemetry" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_listener_telemetry.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}





resource "aws_acm_certificate" "CertificateManagerCertificate" {
  domain_name = local.domain_name
  subject_alternative_names = [
    "*.${local.domain_name}"
  ]
  validation_method = "DNS"
}