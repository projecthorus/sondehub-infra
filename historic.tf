data "archive_file" "historic_to_s3" {
  type        = "zip"
  source_file = "historic/historic_es_to_s3/index.py"
  output_path = "${path.module}/build/historic_to_s3.zip"
}

data "archive_file" "queue_data_update" {
  type        = "zip"
  source_file = "historic/queue_data_update/index.py"
  output_path = "${path.module}/build/queue_data_update.zip"
}

resource "aws_iam_role" "historic" {
  path                 = "/service-role/"
  name                 = "historic"
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


resource "aws_iam_role_policy" "historic" {
  name   = "historic"
  role   = aws_iam_role.historic.name
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


resource "aws_lambda_function" "historic_to_s3" {
  function_name                  = "historic_to_s3"
  handler                        = "index.handler"
  filename                       = "${path.module}/build/historic_to_s3.zip"
  source_code_hash               = data.archive_file.historic_to_s3.output_base64sha256
  publish                        = true
  memory_size                    = 3096
  role                           = aws_iam_role.historic.arn
  runtime                        = "python3.9"
  timeout                        = 120
  reserved_concurrent_executions = 2
  environment {
    variables = {
      "ES" = aws_route53_record.es.fqdn
    }
  }
}
resource "aws_lambda_function" "queue_data_update" {
  function_name                  = "queue_data_update"
  handler                        = "index.handler"
  filename                       = "${path.module}/build/queue_data_update.zip"
  source_code_hash               = data.archive_file.queue_data_update.output_base64sha256
  publish                        = true
  memory_size                    = 256
  role                           = aws_iam_role.historic.arn
  runtime                        = "python3.9"
  timeout                        = 30
  reserved_concurrent_executions = 1
  environment {
    variables = {
      "ES" = aws_route53_record.es.fqdn
    }
  }
}

resource "aws_sqs_queue" "historic_to_s3" {
  name                      = "update-history"
  receive_wait_time_seconds = 0
  message_retention_seconds = 1209600 # 14 days
  visibility_timeout_seconds = 300
}


resource "aws_lambda_event_source_mapping" "historic_to_s3" {
  event_source_arn                   = aws_sqs_queue.historic_to_s3.arn
  function_name                      = aws_lambda_function.historic_to_s3.arn
  batch_size                         = 1
  maximum_batching_window_in_seconds = 30
}

resource "aws_cloudwatch_event_rule" "history" {
  name        = "history_queue"
  description = "History Queue"

  schedule_expression = "cron(0 15,20,3,9 * * ? *)"
}

resource "aws_cloudwatch_event_target" "sns" {
  rule      = aws_cloudwatch_event_rule.history.name
  target_id = "SendToLambda"
  arn       = aws_lambda_function.queue_data_update.arn
}

resource "aws_lambda_permission" "history_cron" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.queue_data_update.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.history.arn
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

resource "aws_apigatewayv2_integration" "history" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.history.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
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

data "archive_file" "history" {
  type        = "zip"
  source_file = "history/lambda_function.py"
  output_path = "${path.module}/build/history.zip"
}

resource "aws_lambda_function" "history" {
  function_name                  = "history"
  handler                        = "lambda_function.history"
  filename                       = "${path.module}/build/history.zip"
  source_code_hash               = data.archive_file.history.output_base64sha256
  publish                        = true
  memory_size                    = 512
  role                           = aws_iam_role.basic_lambda_role.arn
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


resource "aws_lambda_permission" "history" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.history.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/sonde/{serial}"
}

resource "aws_apigatewayv2_route" "history" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /sonde/{serial}"
  target             = "integrations/${aws_apigatewayv2_integration.history.id}"
}
