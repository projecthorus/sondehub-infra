data "archive_file" "recovered" {
  type        = "zip"
  source_file = "recovered/lambda_function.py"
  output_path = "${path.module}/build/recovered.zip"
}

resource "aws_iam_role" "recovered" {
  path                 = "/service-role/"
  name                 = "recovered"
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


resource "aws_iam_role_policy" "recovered" {
  name   = "recovered"
  role   = aws_iam_role.recovered.name
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
        }
    ]
}
EOF
}


resource "aws_lambda_function" "recovered_get" {
  function_name                  = "recovered_get"
  handler                        = "lambda_function.get"
  filename                       = "${path.module}/build/recovered.zip"
  source_code_hash               = data.archive_file.recovered.output_base64sha256
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
}

resource "aws_lambda_function" "recovered_put" {
  function_name                  = "recovered_put"
  handler                        = "lambda_function.put"
  filename                       = "${path.module}/build/recovered.zip"
  source_code_hash               = data.archive_file.recovered.output_base64sha256
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
}

resource "aws_lambda_permission" "recovered_get" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.recovered_get.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/recovered"
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
resource "aws_apigatewayv2_route" "recovered_put" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "PUT /recovered"
  target             = "integrations/${aws_apigatewayv2_integration.recovered_put.id}"
}