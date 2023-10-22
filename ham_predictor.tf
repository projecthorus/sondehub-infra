resource "aws_iam_role" "ham_predict_updater" {
  path                 = "/service-role/"
  name                 = "ham-predict-updater"
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


resource "aws_iam_role_policy" "ham_predict_updater" {
  name   = "ham_predict_updater"
  role   = aws_iam_role.ham_predict_updater.name
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
        },
        {
            "Effect": "Allow",
            "Action": "es:*",
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": "sqs:*",
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": "s3:*",
            "Resource": "*"
        },
        {
          "Action": [
            "secretsmanager:GetSecretValue"
          ],
          "Effect": "Allow",
          "Resource": ["${aws_secretsmanager_secret.mqtt.arn}", "${aws_secretsmanager_secret.radiosondy.arn}"]
        }
    ]
}
EOF
}


resource "aws_lambda_function" "ham_predict_updater" {
  function_name                  = "ham_predict_updater"
  handler                        = "ham_predict_updater.predict"
  s3_bucket                      = aws_s3_bucket_object.lambda.bucket
  s3_key                         = aws_s3_bucket_object.lambda.key
  source_code_hash               = data.archive_file.lambda.output_base64sha256
  publish                        = true
  memory_size                    = 512
  role                           = aws_iam_role.ham_predict_updater.arn
  runtime                        = "python3.9"
  architectures                  = ["arm64"]
  timeout                        = 300
  reserved_concurrent_executions = 1
  environment {
    variables = {
      "ES"      = aws_route53_record.es.fqdn
      MQTT_HOST = "ws.v2.sondehub.org" # We go via the internet as this function isn't in a VPC
      MQTT_PORT = "443"
    }
  }
  tags = {
    Name = "ham_predict_updater"
  }
}


resource "aws_cloudwatch_event_rule" "ham_predict_updater" {
  name        = "ham_predict_updater"
  description = "ham_predict_updater"

  schedule_expression = "rate(1 minute)"
}

resource "aws_cloudwatch_event_target" "ham_predict_updater" {
  rule      = aws_cloudwatch_event_rule.ham_predict_updater.name
  target_id = "SendToLambda"
  arn       = aws_lambda_function.ham_predict_updater.arn
}

resource "aws_lambda_permission" "ham_predict_updater" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ham_predict_updater.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ham_predict_updater.arn
}




resource "aws_apigatewayv2_route" "ham_predictions" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /amateur/predictions"
  target             = "integrations/${aws_apigatewayv2_integration.ham_predictions.id}"
}
resource "aws_apigatewayv2_integration" "ham_predictions" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.ham_predictions.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}


resource "aws_lambda_function" "ham_predictions" {
  function_name                  = "ham_predictions"
  handler                        = "ham_predict.predict"
  s3_bucket                      = aws_s3_bucket_object.lambda.bucket
  s3_key                         = aws_s3_bucket_object.lambda.key
  source_code_hash               = data.archive_file.lambda.output_base64sha256
  reserved_concurrent_executions = 10
  publish                        = true
  memory_size                    = 128
  role                           = aws_iam_role.basic_lambda_role.arn
  runtime                        = "python3.9"
  timeout                        = 30
  architectures                  = ["arm64"]
  environment {
    variables = {
      "ES" = "es.${local.domain_name}"
    }
  }
  tags = {
    Name = "ham_predictions"
  }
}
resource "aws_lambda_permission" "ham_predictions" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ham_predictions.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/amateur/predictions"
}
