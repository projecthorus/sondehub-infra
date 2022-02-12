
resource "aws_lambda_function" "get_sondes" {
  function_name    = "query"
  handler          = "query.get_sondes"
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
    Name = "query"
  }
}






resource "aws_lambda_function" "get_telem" {
  function_name    = "get_telem"
  handler          = "query.get_telem"
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
    Name = "get_telem"
  }
}

resource "aws_lambda_function" "get_sites" {
  function_name    = "get_sites"
  handler          = "query.get_sites"
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
    Name = "get_sites"
  }
}

resource "aws_lambda_function" "get_listener_telemetry" {
  function_name    = "get_listener_telemetry"
  handler          = "query.get_listener_telemetry"
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
    Name = "get_listener_telemetry"
  }
}



resource "aws_lambda_function" "get_listener_stats" {
  function_name    = "get_listener_stats"
  handler          = "query.telm_stats"
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
    Name = "get_listener_stats"
  }
}



resource "aws_lambda_permission" "get_sondes" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_sondes.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/sondes"
}

resource "aws_lambda_permission" "get_sites" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_sites.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/sites"
}

resource "aws_lambda_permission" "get_listeners_stats" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_listener_stats.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/listeners/stats"
}

resource "aws_lambda_permission" "get_listener_stats" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_listener_stats.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/listener/stats"
}




resource "aws_lambda_permission" "get_telem" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_telem.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/sondes/telemetry"
}
resource "aws_lambda_permission" "get_listener_telemetry" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_listener_telemetry.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/listeners/telemetry"
}

resource "aws_apigatewayv2_route" "get_sondes" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /sondes"
  target             = "integrations/${aws_apigatewayv2_integration.get_sondes.id}"
}

resource "aws_apigatewayv2_route" "get_sites" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /sites"
  target             = "integrations/${aws_apigatewayv2_integration.get_sites.id}"
}


resource "aws_apigatewayv2_route" "get_listeners_stats" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /listeners/stats"
  target             = "integrations/${aws_apigatewayv2_integration.get_listener_stats.id}"
}

resource "aws_apigatewayv2_route" "get_listener_stats" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /listener/stats"
  target             = "integrations/${aws_apigatewayv2_integration.get_listener_stats.id}"
}



resource "aws_apigatewayv2_route" "get_telem" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /sondes/telemetry"
  target             = "integrations/${aws_apigatewayv2_integration.get_telem.id}"
}

resource "aws_apigatewayv2_route" "get_listener_telemetry" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /listeners/telemetry"
  target             = "integrations/${aws_apigatewayv2_integration.get_listener_telemetry.id}"
}




resource "aws_apigatewayv2_integration" "get_sondes" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_sondes.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "get_sites" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_sites.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}




resource "aws_apigatewayv2_integration" "get_telem" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_telem.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "get_listener_telemetry" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_listener_telemetry.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "get_listener_stats" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_listener_stats.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}


