resource "aws_lambda_function" "tile_counts" {
  function_name    = "tile_counts"
  handler          = "tile_counts.lambda_handler"
  s3_bucket        = aws_s3_bucket_object.lambda.bucket
  s3_key           = aws_s3_bucket_object.lambda.key
  source_code_hash = data.archive_file.lambda.output_base64sha256
  publish          = true
  memory_size      = 128
  role             = aws_iam_role.basic_lambda_role.arn
  runtime          = "python3.9"
  timeout          = 10
  architectures    = ["arm64"]
}

resource "aws_lambda_permission" "tile_counts" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.tile_counts.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/tiles/count"
}

resource "aws_apigatewayv2_route" "tile_counts" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "PUT /tiles/count"
  target             = "integrations/${aws_apigatewayv2_integration.tile_counts.id}"
}

resource "aws_apigatewayv2_integration" "tile_counts" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.tile_counts.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}