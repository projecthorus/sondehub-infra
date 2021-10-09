resource "aws_apigatewayv2_route" "sign_socket" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /sondes/websocket"
  target             = "integrations/${aws_apigatewayv2_integration.sign_socket.id}"
}

resource "aws_iam_role" "sign_socket" {
  name                 = "sign_socket"
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

data "archive_file" "sign_socket" {
  type        = "zip"
  source_file = "sign-websocket/lambda_function.py"
  output_path = "${path.module}/build/sign_socket.zip"
}

resource "aws_lambda_function" "sign_socket" {
  function_name    = "sign-websocket"
  handler          = "lambda_function.lambda_handler"
  filename         = "${path.module}/build/sign_socket.zip"
  source_code_hash = data.archive_file.sign_socket.output_base64sha256
  publish          = true
  memory_size      = 128
  role             = aws_iam_role.sign_socket.arn
  runtime          = "python3.9"
  timeout          = 10
  architectures    = ["arm64"]
}

resource "aws_lambda_permission" "sign_socket" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sign_socket.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/sondes/websocket"
}

resource "aws_apigatewayv2_integration" "sign_socket" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.sign_socket.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}



# TODO subnet for reader
# padding interfaces