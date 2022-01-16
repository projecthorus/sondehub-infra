resource "aws_sns_topic" "ham_telem" {
  name            = "ham-telem"
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


resource "aws_iam_role" "ham_sqs_to_elk" {
  path                 = "/service-role/"
  name                 = "ham_sqs-to-elk"
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


resource "aws_iam_role_policy" "ham_sqs_to_elk" {
  name   = "ham_sqs_to_elk"
  role   = aws_iam_role.ham_sqs_to_elk.name
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
        }
    ]
}
EOF
}

resource "aws_lambda_function" "ham_sqs_to_elk" {
  function_name                  = "ham-sqs-to-elk"
  handler                        = "ham_sqs_to_elk.lambda_handler"
  s3_bucket                      = aws_s3_bucket_object.lambda.bucket
  s3_key                         = aws_s3_bucket_object.lambda.key
  source_code_hash               = data.archive_file.lambda.output_base64sha256
  publish                        = true
  memory_size                    = 128
  role                           = aws_iam_role.ham_sqs_to_elk.arn
  runtime                        = "python3.9"
  timeout                        = 5
  reserved_concurrent_executions = 100
  environment {
    variables = {
      "ES" = aws_route53_record.es.fqdn
    }
  }
  tags = {
    Name = "ham_sqs_to_elk"
  }
}

resource "aws_lambda_event_source_mapping" "ham_sqs_to_elk" {
  event_source_arn                   = aws_sqs_queue.ham_sqs_to_elk.arn
  function_name                      = aws_lambda_function.ham_sqs_to_elk.arn
  batch_size                         = 20
  maximum_batching_window_in_seconds = 15
}

resource "aws_sns_topic_subscription" "ham_sqs_to_elk" {
  topic_arn = aws_sns_topic.ham_telem.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.ham_sqs_to_elk.arn
}

resource "aws_sqs_queue" "ham_sqs_to_elk" {
  name                      = "ham-to-elk"
  receive_wait_time_seconds = 1
  message_retention_seconds = 1209600 # 14 days

  redrive_policy = jsonencode(
    {
      deadLetterTargetArn = aws_sqs_queue.ham_sqs_to_elk_dlq.arn
      maxReceiveCount     = 100
    }
  )
}

resource "aws_sqs_queue" "ham_sqs_to_elk_dlq" {
  name                      = "ham-to-elk-dlq"
  receive_wait_time_seconds = 1
  message_retention_seconds = 1209600 # 14 days

}

resource "aws_sqs_queue_policy" "ham_sqs_to_elk" {
  queue_url = aws_sqs_queue.ham_sqs_to_elk.id
  policy    = <<EOF
{
  "Version": "2008-10-17",
  "Id": "__default_policy_ID",
  "Statement": [
    {
      "Sid": "__owner_statement",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
      },
      "Action": "SQS:*",
      "Resource": "${aws_sqs_queue.ham_sqs_to_elk.arn}"
    },
    {
      "Sid": "to-elk",
      "Effect": "Allow",
      "Principal": {
        "AWS": "*"
      },
      "Action": "SQS:SendMessage",
      "Resource": "${aws_sqs_queue.ham_sqs_to_elk.arn}",
      "Condition": {
        "ArnLike": {
          "aws:SourceArn": "${aws_sns_topic.ham_telem.arn}"
        }
      }
    }
  ]
}
EOF
}


// PUT api

resource "aws_lambda_function" "ham_upload_telem" {
  function_name    = "ham-put-api"
  handler          = "ham_put_api.lambda_handler"
  s3_bucket        = aws_s3_bucket_object.lambda.bucket
  s3_key           = aws_s3_bucket_object.lambda.key
  source_code_hash = data.archive_file.lambda.output_base64sha256
  publish          = true
  memory_size      = 128
  role             = aws_iam_role.basic_lambda_role.arn
  runtime          = "python3.9"
  timeout          = 30
  architectures    = ["arm64"]
  environment {
    variables = {
      "HAM_SNS_TOPIC" = aws_sns_topic.ham_telem.arn
    }
  }
}

resource "aws_lambda_permission" "ham_upload_telem" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ham_upload_telem.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/amateur/telemetry"
}

resource "aws_apigatewayv2_route" "ham_upload_telem" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "PUT /amateur/telemetry"
  target             = "integrations/${aws_apigatewayv2_integration.ham_upload_telem.id}"
}

resource "aws_apigatewayv2_integration" "ham_upload_telem" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.ham_upload_telem.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

// SNS to MQTT

resource "aws_lambda_function" "ham_sns_to_mqtt" {
  function_name = "ham-sns-to-mqtt"
  handler       = "sns_to_mqtt.lambda_handler"
  s3_bucket        = aws_s3_bucket_object.lambda.bucket
  s3_key           = aws_s3_bucket_object.lambda.key
  source_code_hash = data.archive_file.lambda.output_base64sha256
  publish       = true
  memory_size   = 128
  role          = aws_iam_role.basic_lambda_role.arn
  runtime       = "python3.9"
  timeout       = 3
  architectures = ["arm64"]
  lifecycle {
    ignore_changes = [environment]
  }
  tags = {
    Name = "sns-to-mqtt"
  }

}

resource "aws_lambda_permission" "ham_sns_to_mqtt" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ham_sns_to_mqtt.arn
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.ham_telem.arn
}

resource "aws_sns_topic_subscription" "ham_sns_to_mqtt" {
  topic_arn = aws_sns_topic.ham_telem.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.ham_sns_to_mqtt.arn
}