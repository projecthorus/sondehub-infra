
resource "aws_iam_role" "recovered" {
  path                 = "/service-role/"
  name                 = "recovered"
  assume_role_policy   = data.aws_iam_policy_document.lambda_assume_role_policy.json
  max_session_duration = 3600
}

data "aws_iam_policy_document" "recovered" {
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
    resources = [
      aws_secretsmanager_secret.mqtt.arn,
      aws_secretsmanager_secret.radiosondy.arn,
    ]

    actions = ["secretsmanager:GetSecretValue"]
  }
}

resource "aws_iam_role_policy" "recovered" {
  name   = "recovered"
  role   = aws_iam_role.recovered.name
  policy = data.aws_iam_policy_document.recovered.json
}


resource "aws_lambda_function" "recovered_get" {
  function_name                  = "recovered_get"
  handler                        = "recovered.get"
  s3_bucket                      = aws_s3_bucket_object.lambda.bucket
  s3_key                         = aws_s3_bucket_object.lambda.key
  source_code_hash               = data.archive_file.lambda.output_base64sha256
  publish                        = true
  memory_size                    = 128
  role                           = aws_iam_role.recovered.arn
  runtime                        = "python3.9"
  timeout                        = 30
  reserved_concurrent_executions = 100
  environment {
    variables = {
      "ES" = aws_route53_record.es.fqdn
    }
  }
  tags = {
    Name = "recovered_get"
  }
}


resource "aws_lambda_function" "recovered_stats" {
  function_name                  = "recovered_stats"
  handler                        = "recovered.stats"
  s3_bucket                      = aws_s3_bucket_object.lambda.bucket
  s3_key                         = aws_s3_bucket_object.lambda.key
  source_code_hash               = data.archive_file.lambda.output_base64sha256
  publish                        = true
  memory_size                    = 128
  role                           = aws_iam_role.recovered.arn
  runtime                        = "python3.9"
  timeout                        = 30
  reserved_concurrent_executions = 100
  environment {
    variables = {
      "ES" = aws_route53_record.es.fqdn
    }
  }
  tags = {
    Name = "recovered_stats"
  }
}


resource "aws_lambda_function" "recovered_put" {
  function_name                  = "recovered_put"
  handler                        = "recovered.put"
  s3_bucket                      = aws_s3_bucket_object.lambda.bucket
  s3_key                         = aws_s3_bucket_object.lambda.key
  source_code_hash               = data.archive_file.lambda.output_base64sha256
  publish                        = true
  memory_size                    = 128
  role                           = aws_iam_role.recovered.arn
  runtime                        = "python3.9"
  timeout                        = 30
  reserved_concurrent_executions = 100
  environment {
    variables = {
      "ES" = aws_route53_record.es.fqdn
    }
  }
  tags = {
    Name = "recovered_put"
  }
}

resource "aws_lambda_permission" "recovered_get" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.recovered_get.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/recovered"
}

resource "aws_lambda_permission" "recovered_stats" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.recovered_stats.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/recovered/stats"
}

resource "aws_lambda_permission" "recovered_put" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.recovered_put.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/recovered"
}

resource "aws_apigatewayv2_integration" "recovered_get" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.recovered_get.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "recovered_stats" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.recovered_stats.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "recovered_put" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.recovered_put.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}
resource "aws_apigatewayv2_route" "recovered_get" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /recovered"
  target             = "integrations/${aws_apigatewayv2_integration.recovered_get.id}"
}

resource "aws_apigatewayv2_route" "recovered_stats" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /recovered/stats"
  target             = "integrations/${aws_apigatewayv2_integration.recovered_stats.id}"
}

resource "aws_apigatewayv2_route" "recovered_put" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "PUT /recovered"
  target             = "integrations/${aws_apigatewayv2_integration.recovered_put.id}"
}


resource "aws_lambda_function" "recovery_ingest" {
  function_name    = "recovery_ingest"
  handler          = "recovery_ingest.handler"
  s3_bucket        = aws_s3_bucket_object.lambda.bucket
  s3_key           = aws_s3_bucket_object.lambda.key
  source_code_hash = data.archive_file.lambda.output_base64sha256
  publish          = true
  memory_size      = 128
  role             = aws_iam_role.recovered.arn
  runtime          = "python3.9"
  timeout          = 300

  tags = {
    Name = "recovered_get"
  }
  environment {
    variables = {}
  }
}


resource "aws_cloudwatch_event_rule" "recovery_ingest" {
  name        = "recovery_ingest"
  description = "recovery_ingest"

  schedule_expression = "cron(*/5 * * * ? *)"
}

resource "aws_cloudwatch_event_target" "recovery_ingest" {
  rule      = aws_cloudwatch_event_rule.recovery_ingest.name
  target_id = "recovery_ingest"
  arn       = aws_lambda_function.recovery_ingest.arn
}

resource "aws_lambda_permission" "recovery_ingest" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.recovery_ingest.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.recovery_ingest.arn
}