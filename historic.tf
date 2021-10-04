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
  memory_size                    = 2048
  role                           = aws_iam_role.historic.arn
  runtime                        = "python3.9"
  timeout                        = 60
  reserved_concurrent_executions = 2
  environment {
    variables = {
      "ES" = aws_route53_record.Route53RecordSet7.fqdn
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
      "ES" = aws_route53_record.Route53RecordSet7.fqdn
    }
  }
}

resource "aws_lambda_event_source_mapping" "historic_to_s3" {
  event_source_arn                   = "arn:aws:sqs:us-east-1:143841941773:update-history"
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