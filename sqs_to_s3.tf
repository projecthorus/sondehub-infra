data "archive_file" "sqs_to_s3" {
  type        = "zip"
  source_dir = "sonde-to-s3/"
  output_path = "${path.module}/build/sonde-to-s3.zip"
}

resource "aws_iam_role" "sqs_to_s3" {
  path                 = "/service-role/"
  name                 = "sqs_to_s3"
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


resource "aws_iam_role_policy" "sqs_to_s3" {
  name   = "sqs_to_s3"
  role   = aws_iam_role.sqs_to_s3.name
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
            "Action": [
              "ec2:DescribeInstances",
              "ec2:CreateNetworkInterface",
              "ec2:AttachNetworkInterface",
              "ec2:DescribeNetworkInterfaces",
              "ec2:DeleteNetworkInterface"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": "s3:*",
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

resource "aws_lambda_function" "sqs_to_s3" {
  function_name                  = "sqs_to_s3"
  handler                        = "lambda_function.lambda_handler"
  filename                       = "${path.module}/build/sonde-to-s3.zip"
  source_code_hash               = data.archive_file.sqs_to_s3.output_base64sha256
  publish                        = true
  memory_size                    = 128
  role                           = aws_iam_role.sqs_to_s3.arn
  runtime                        = "python3.8"
  timeout                        = 30
  reserved_concurrent_executions = 100
  vpc_config {
    security_group_ids = ["sg-772f357f"]
    subnet_ids = ["subnet-5c34ec6d", "subnet-7b1c3836", "subnet-204b052e", "subnet-de4ddeff", "subnet-408d1c1f", "subnet-a7f460c1"]
  }
}

resource "aws_lambda_event_source_mapping" "sqs_to_s3" {
  event_source_arn                   = aws_sqs_queue.sqs_to_s3.arn
  function_name                      = aws_lambda_function.sqs_to_s3.arn
  batch_size                         = 40
  maximum_batching_window_in_seconds = 15
}

resource "aws_sns_topic_subscription" "sqs_to_s3" {
  topic_arn = aws_sns_topic.sonde_telem.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.sqs_to_s3.arn
}

resource "aws_sqs_queue" "sqs_to_s3" {
  name                      = "to-s3"
  receive_wait_time_seconds = 1
  message_retention_seconds = 1209600 # 14 days
}

resource "aws_sqs_queue_policy" "sqs_to_s3" {
  queue_url = aws_sqs_queue.sqs_to_s3.id
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
      "Resource": "${aws_sqs_queue.sqs_to_s3.arn}"
    },
    {
      "Sid": "to-s3",
      "Effect": "Allow",
      "Principal": {
        "AWS": "*"
      },
      "Action": "SQS:SendMessage",
      "Resource": "${aws_sqs_queue.sqs_to_s3.arn}",
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
