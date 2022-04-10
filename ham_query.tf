
resource "aws_lambda_function" "ham_get" {
  function_name    = "ham_get"
  handler          = "query_ham.get"
  s3_bucket        = aws_s3_bucket_object.lambda.bucket
  s3_key           = aws_s3_bucket_object.lambda.key
  source_code_hash = data.archive_file.lambda.output_base64sha256
  publish          = true
  memory_size      = 256
  role             = aws_iam_role.basic_lambda_role.arn
  runtime          = "python3.9"
  timeout          = 30
  architectures    = ["arm64"]
  environment {
    variables = {
      "ES" = "es.${local.domain_name}"
    }
  }
  tags = {
    Name = "ham_get"
  }
}






resource "aws_lambda_function" "ham_telem" {
  function_name    = "ham_get_telem"
  handler          = "query_ham.get_telem"
  s3_bucket        = aws_s3_bucket_object.lambda.bucket
  s3_key           = aws_s3_bucket_object.lambda.key
  source_code_hash = data.archive_file.lambda.output_base64sha256
  publish          = true
  memory_size      = 256
  role             = aws_iam_role.basic_lambda_role.arn
  runtime          = "python3.9"
  timeout          = 30
  architectures    = ["arm64"]
  environment {
    variables = {
      "ES" = "es.${local.domain_name}"
    }
  }
  tags = {
    Name = "ham_get_telem"
  }
}

resource "aws_lambda_permission" "ham_get" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ham_get.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/amateur"
}

resource "aws_lambda_permission" "ham_telem" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ham_telem.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/amateur/telemetry"
}


resource "aws_apigatewayv2_route" "ham_get" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /amateur"
  target             = "integrations/${aws_apigatewayv2_integration.ham_get.id}"
}

resource "aws_apigatewayv2_route" "ham_telem" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /amateur/telemetry"
  target             = "integrations/${aws_apigatewayv2_integration.ham_telem.id}"
}

resource "aws_apigatewayv2_integration" "ham_get" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.ham_get.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "ham_telem" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.ham_telem.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}


resource "aws_lambda_function" "ham_get_listener_telemetry" {
  function_name    = "ham_get_listener_telemetry"
  handler          = "query_ham.get_listener_telemetry"
  s3_bucket        = aws_s3_bucket_object.lambda.bucket
  s3_key           = aws_s3_bucket_object.lambda.key
  source_code_hash = data.archive_file.lambda.output_base64sha256
  publish          = true
  memory_size      = 256
  role             = aws_iam_role.basic_lambda_role.arn
  runtime          = "python3.9"
  timeout          = 30
  architectures    = ["arm64"]
  environment {
    variables = {
      "ES" = "es.${local.domain_name}"
    }
  }
  tags = {
    Name = "ham_get_listener_telemetry"
  }
}

resource "aws_lambda_permission" "ham_get_listener_telemetry" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ham_get_listener_telemetry.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/amateur/listeners/telemetry"
}

resource "aws_apigatewayv2_route" "ham_get_listener_telemetry" {
    api_id             = aws_apigatewayv2_api.main.id
    api_key_required   = false
    authorization_type = "NONE"
    route_key          = "GET /amateur/listeners/telemetry"
    target             = "integrations/${aws_apigatewayv2_integration.ham_get_listener_telemetry.id}"
}


resource "aws_apigatewayv2_integration" "ham_get_listener_telemetry" {
    api_id                 = aws_apigatewayv2_api.main.id
    connection_type        = "INTERNET"
    integration_method     = "POST"
    integration_type       = "AWS_PROXY"
    integration_uri        = aws_lambda_function.ham_get_listener_telemetry.arn
    timeout_milliseconds   = 30000
    payload_format_version = "2.0"
}