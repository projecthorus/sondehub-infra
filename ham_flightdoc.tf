# cognito auth role

resource "aws_lambda_function" "ham_flight_doc" {
  function_name    = "ham-put-flight-doc"
  handler          = "ham_update_flight_doc.lambda_handler"
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
      "ES" = "es.${local.domain_name}"
    }
  }
}

resource "aws_lambda_permission" "ham_flight_doc" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ham_flight_doc.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/amateur/flightdoc"
}

resource "aws_apigatewayv2_route" "ham_flight_doc" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "AWS_IAM"
  route_key          = "PUT /amateur/flightdoc"
  target             = "integrations/${aws_apigatewayv2_integration.ham_flight_doc.id}"
}

resource "aws_apigatewayv2_integration" "ham_flight_doc" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.ham_flight_doc.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}