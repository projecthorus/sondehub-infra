data "archive_file" "predict_updater" {
  type        = "zip"
  source_file = "predict_updater/lambda_function.py"
  output_path = "${path.module}/build/predict_updater.zip"
}

resource "aws_iam_role" "predict_updater" {
  path                 = "/service-role/"
  name                 = "predict-updater"
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


resource "aws_iam_role_policy" "predict_updater" {
  name   = "predict_updater"
  role   = aws_iam_role.predict_updater.name
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
        }
    ]
}
EOF
}


resource "aws_lambda_function" "predict_updater" {
  function_name                  = "predict_updater"
  handler                        = "lambda_function.predict"
  filename                       = "${path.module}/build/predict_updater.zip"
  source_code_hash               = data.archive_file.predict_updater.output_base64sha256
  publish                        = true
  memory_size                    = 256
  role                           = aws_iam_role.predict_updater.arn
  runtime                        = "python3.9"
  architectures                  = ["arm64"]
  timeout                        = 60
  reserved_concurrent_executions = 8
  environment {
    variables = {
      "ES" = aws_route53_record.es.fqdn
    }
  }
}


resource "aws_cloudwatch_event_rule" "predict_updater" {
  name        = "predict_updater"
  description = "predict_updater"

  schedule_expression = "rate(1 minute)"
}

resource "aws_cloudwatch_event_target" "predict_updater" {
  rule      = aws_cloudwatch_event_rule.predict_updater.name
  target_id = "SendToLambda"
  arn       = aws_lambda_function.predict_updater.arn
}

resource "aws_lambda_permission" "predict_updater" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.predict_updater.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.predict_updater.arn
}

resource "aws_apigatewayv2_route" "predictions" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /predictions"
  target             = "integrations/${aws_apigatewayv2_integration.predictions.id}"
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

data "archive_file" "predictions" {
  type        = "zip"
  source_file = "predict/lambda_function.py"
  output_path = "${path.module}/build/predictions.zip"
}

resource "aws_lambda_function" "predictions" {
  function_name    = "predictions"
  handler          = "lambda_function.predict"
  filename         = "${path.module}/build/predictions.zip"
  source_code_hash = data.archive_file.predictions.output_base64sha256
  publish          = true
  memory_size      = 128
  role             = aws_iam_role.basic_lambda_role.arn
  runtime          = "python3.9"
  timeout          = 30
  architectures    = ["arm64"]
  environment {
    variables = {
      "ES" = "es.${local.domain_name}"
    }
  }
}
resource "aws_lambda_permission" "predictions" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.predictions.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/predictions"
}
