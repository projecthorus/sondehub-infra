

resource "aws_iam_role" "historic" {
  path                 = "/service-role/"
  name                 = "historic"
  assume_role_policy   = data.aws_iam_policy_document.lambda_assume_role_policy.json
  max_session_duration = 3600
}

data "aws_iam_policy_document" "historic" {
  statement {
    resources = ["arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:*"]
    actions   = ["logs:CreateLogGroup"]
  }

  statement {
    resources = ["arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/*"]

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
  }

  statement {
    resources = ["*"]
    actions   = ["es:*"]
  }

  statement {
    resources = ["*"]
    actions   = ["sqs:*"]
  }

  statement {
    resources = ["*"]
    actions   = ["s3:*"]
  }
}

resource "aws_iam_role_policy" "historic" {
  name   = "historic"
  role   = aws_iam_role.historic.name
  policy = data.aws_iam_policy_document.historic.json
}


resource "aws_lambda_function" "historic_to_s3" {
  function_name                  = "historic_to_s3"
  handler                        = "historic_es_to_s3.handler"
  s3_bucket                      = aws_s3_bucket_object.lambda.bucket
  s3_key                         = aws_s3_bucket_object.lambda.key
  source_code_hash               = data.archive_file.lambda.output_base64sha256
  publish                        = true
  memory_size                    = 8192
  role                           = aws_iam_role.historic.arn
  runtime                        = "python3.9"
  timeout                        = 300
  reserved_concurrent_executions = 2
  environment {
    variables = {
      "ES" = aws_route53_record.es.fqdn
    }
  }
  tags = {
    Name = "historic_to_s3"
  }
}
resource "aws_lambda_function" "queue_data_update" {
  function_name                  = "queue_data_update"
  handler                        = "queue_data_update.handler"
  s3_bucket                      = aws_s3_bucket_object.lambda.bucket
  s3_key                         = aws_s3_bucket_object.lambda.key
  source_code_hash               = data.archive_file.lambda.output_base64sha256
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
  tags = {
    Name = "queue_data_update"
  }
}

resource "aws_sqs_queue" "historic_to_s3" {
  name                       = "update-history"
  receive_wait_time_seconds  = 0
  message_retention_seconds  = 259200
  visibility_timeout_seconds = 3600


  redrive_policy = jsonencode(
    {
      deadLetterTargetArn = aws_sqs_queue.historic_to_s3_dlq.arn
      maxReceiveCount     = 100
    }
  )
}

resource "aws_sqs_queue" "historic_to_s3_dlq" {
  name                       = "update-history-dlq"
  receive_wait_time_seconds  = 1
  message_retention_seconds  = 1209600 # 14 days
  visibility_timeout_seconds = 10
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
  assume_role_policy   = data.aws_iam_policy_document.lambda_assume_role_policy.json
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

data "aws_iam_policy_document" "history" {
  statement {
    resources = ["arn:aws:s3:::sondehub-open-data/*"]
    actions   = ["s3:*"]
  }

  statement {
    resources = ["arn:aws:s3:::sondehub-open-data"]
    actions   = ["s3:*"]
  }

  statement {
    resources = ["arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:*"]
    actions   = ["logs:CreateLogGroup"]
  }

  statement {
    resources = ["arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/*"]

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
  }

  statement {
    resources = ["arn:aws:es:us-east-1:${data.aws_caller_identity.current.account_id}:domain/sondes-v2*"]
    actions   = ["es:*"]
  }

  statement {
    resources = ["arn:aws:es:us-east-1:${data.aws_caller_identity.current.account_id}:domain/sondes-v2*"]
    actions   = ["es:*"]
  }
}


resource "aws_iam_role_policy" "history" {
  policy = data.aws_iam_policy_document.history.json
  role   = aws_iam_role.history.name
}


resource "aws_lambda_function" "history" {
  function_name                  = "history"
  handler                        = "history.history"
  s3_bucket                      = aws_s3_bucket_object.lambda.bucket
  s3_key                         = aws_s3_bucket_object.lambda.key
  source_code_hash               = data.archive_file.lambda.output_base64sha256
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

  tags = {
    Name = "history"
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
