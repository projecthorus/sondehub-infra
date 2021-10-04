data "archive_file" "sqs_to_elk" {
  type        = "zip"
  source_file = "sqs-to-elk/lambda_function.py"
  output_path = "${path.module}/build/sqs-to-elk.zip"
}

resource "aws_iam_role" "sqs_to_elk" {
  path                 = "/service-role/"
  name                 = "sqs-to-elk"
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


resource "aws_iam_role_policy" "sqs_to_elk" {
  name   = "sqs_to_elk"
  role   = aws_iam_role.sqs_to_elk.name
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

resource "aws_lambda_function" "sqs_to_elk" {
  function_name                  = "sqs-to-elk"
  handler                        = "lambda_function.lambda_handler"
  filename                       = "${path.module}/build/sqs-to-elk.zip"
  source_code_hash               = data.archive_file.sqs_to_elk.output_base64sha256
  publish                        = true
  memory_size                    = 128
  role                           = aws_iam_role.sqs_to_elk.arn
  runtime                        = "python3.9"
  timeout                        = 5
  reserved_concurrent_executions = 100
  environment {
    variables = {
      "ES" = aws_route53_record.Route53RecordSet7.fqdn
    }
  }
}

resource "aws_lambda_event_source_mapping" "sqs_to_elk" {
  event_source_arn                   = aws_sqs_queue.sqs_to_elk.arn
  function_name                      = aws_lambda_function.sqs_to_elk.arn
  batch_size                         = 20
  maximum_batching_window_in_seconds = 15
}

resource "aws_sns_topic_subscription" "sqs_to_elk" {
  topic_arn = aws_sns_topic.sonde_telem.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.sqs_to_elk.arn
}

resource "aws_sqs_queue" "sqs_to_elk" {
  name                      = "to-elk"
  receive_wait_time_seconds = 1
  message_retention_seconds = 1209600 # 14 days
}

resource "aws_sqs_queue_policy" "sqs_to_elk" {
  queue_url = aws_sqs_queue.sqs_to_elk.id
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
      "Resource": "${aws_sqs_queue.sqs_to_elk.arn}"
    },
    {
      "Sid": "to-elk",
      "Effect": "Allow",
      "Principal": {
        "AWS": "*"
      },
      "Action": "SQS:SendMessage",
      "Resource": "${aws_sqs_queue.sqs_to_elk.arn}",
      "Condition": {
        "ArnLike": {
          "aws:SourceArn": "${aws_sns_topic.sonde_telem.arn}"
        }
      }
    }
  ]
}
EOF
}