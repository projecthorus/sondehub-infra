
resource "aws_iam_role" "ingestion_lambda_role" { # need a specific role so that we can disable cloudwatch logs
  path                 = "/service-role/"
  name_prefix          = "sonde-ingestion-"
  assume_role_policy   = data.aws_iam_policy_document.lambda_assume_role_policy.json
  max_session_duration = 3600
}


data "aws_iam_policy_document" "ingestion" {
  statement {
    resources = ["*"]
    actions   = ["s3:*"]
  }

  statement {
    resources = ["*"]
    actions   = ["sns:*"]
  }

  statement {
    resources = ["arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:*"]
    actions   = ["logs:CreateLogGroup"]
  }

  statement {
    resources = [
      "arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:log-group:/ingestion",
      "arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:log-group:/sns_to_mqtt",
    ]

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
  }

  statement {
    resources = [
      "arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:log-group:/ingestion*",
      "arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:log-group:/sns_to_mqtt*",
    ]

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
  }

  statement {
    resources = ["*"]

    actions = [
      "ec2:DescribeNetworkInterfaces",
      "ec2:CreateNetworkInterface",
      "ec2:DeleteNetworkInterface",
      "ec2:DescribeInstances",
      "ec2:AttachNetworkInterface",
    ]
  }

  statement {

    resources = [
      aws_secretsmanager_secret.mqtt.arn,
      aws_secretsmanager_secret.radiosondy.arn,
    ]

    actions = ["secretsmanager:GetSecretValue"]
  }
}

resource "aws_iam_role_policy" "ingestion_lambda_role" {
  policy = data.aws_iam_policy_document.ingestion.json
  role   = aws_iam_role.ingestion_lambda_role.name
}

resource "aws_cloudwatch_log_group" "ignestion" {
  name = "/ingestion"
}

resource "aws_cloudwatch_log_group" "sns_to_mqtt" {
  name = "/sns_to_mqtt"
}

resource "aws_lambda_function" "upload_telem" {
  function_name    = "sonde-api-to-iot-core"
  handler          = "sonde_api_to_iot_core.lambda_handler"
  s3_bucket        = aws_s3_bucket_object.lambda.bucket
  s3_key           = aws_s3_bucket_object.lambda.key
  source_code_hash = data.archive_file.lambda.output_base64sha256
  publish          = true
  memory_size      = 128
  role             = aws_iam_role.ingestion_lambda_role.arn
  runtime          = "python3.9"
  timeout          = 30
  architectures    = ["arm64"]
  environment {
    variables = {
      "SNS_TOPIC" = aws_sns_topic.sonde_telem.arn
    }
  }
}

resource "aws_lambda_function" "station" {
  function_name    = "station-api-to-iot-core"
  handler          = "station_api_to_iot_core.lambda_handler"
  s3_bucket        = aws_s3_bucket_object.lambda.bucket
  s3_key           = aws_s3_bucket_object.lambda.key
  source_code_hash = data.archive_file.lambda.output_base64sha256
  publish          = true
  memory_size      = 128
  role             = aws_iam_role.basic_lambda_role.arn
  runtime          = "python3.9"
  timeout          = 10
  architectures    = ["arm64"]
  environment {
    variables = {
      "ES"        = "es.${local.domain_name}"
      "SNS_TOPIC" = aws_sns_topic.listener_telem.arn
    }
  }
  tags = {
    Name = "station-api-to-iot-core"
  }
}

resource "aws_lambda_permission" "station" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.station.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/listeners"
}

resource "aws_lambda_permission" "upload_telem" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.upload_telem.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/sondes/telemetry"
}

resource "aws_apigatewayv2_route" "stations" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "PUT /listeners"
  target             = "integrations/${aws_apigatewayv2_integration.stations.id}"
}

resource "aws_apigatewayv2_route" "upload_telem" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "PUT /sondes/telemetry"
  target             = "integrations/${aws_apigatewayv2_integration.upload_telem.id}"
}

resource "aws_apigatewayv2_integration" "upload_telem" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.upload_telem.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "stations" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.station.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_sns_topic" "sonde_telem" {
  name            = "sonde-telem"
  delivery_policy = <<EOF
{
  "http": {
    "defaultHealthyRetryPolicy": {
      "minDelayTarget": 5,
      "maxDelayTarget": 30,
      "numRetries": 100,
      "numMaxDelayRetries": 0,
      "numNoDelayRetries": 3,
      "numMinDelayRetries": 0,
      "backoffFunction": "linear"
    },
    "disableSubscriptionOverrides": false
  }
}
EOF
}

resource "aws_sns_topic" "listener_telem" {
  name            = "listener-telem"
  delivery_policy = <<EOF
{
  "http": {
    "defaultHealthyRetryPolicy": {
      "minDelayTarget": 5,
      "maxDelayTarget": 30,
      "numRetries": 100,
      "numMaxDelayRetries": 0,
      "numNoDelayRetries": 3,
      "numMinDelayRetries": 0,
      "backoffFunction": "linear"
    },
    "disableSubscriptionOverrides": false
  }
}
EOF
}

// SNS to MQTT

resource "aws_lambda_function" "sns_to_mqtt" {
  function_name    = "sns-to-mqtt"
  handler          = "sns_to_mqtt.lambda_handler"
  s3_bucket        = aws_s3_bucket_object.lambda.bucket
  s3_key           = aws_s3_bucket_object.lambda.key
  source_code_hash = data.archive_file.lambda.output_base64sha256
  publish          = true
  memory_size      = 128
  role             = aws_iam_role.ingestion_lambda_role.arn
  runtime          = "python3.9"
  timeout          = 3
  architectures    = ["arm64"]
  environment {
    variables = {
      MQTT_BATCH  = "batch"
      MQTT_ID     = "serial"
      MQTT_PREFIX = "sondes"
    }
  }
  tags = {
    Name = "sns-to-mqtt"
  }

  vpc_config {
    security_group_ids = [
      "sg-05f795128b295c504",
    ]
    subnet_ids = [
      aws_subnet.private["us-east-1b"].id
    ]
  }

}

resource "aws_lambda_permission" "sns_to_mqtt" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.station.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = aws_sns_topic.sonde_telem.arn
}


resource "aws_lambda_function" "sns_to_mqtt_listener" {
  function_name    = "sns-to-mqtt-listener"
  handler          = "sns_to_mqtt.lambda_handler"
  s3_bucket        = aws_s3_bucket_object.lambda.bucket
  s3_key           = aws_s3_bucket_object.lambda.key
  source_code_hash = data.archive_file.lambda.output_base64sha256
  publish          = true
  memory_size      = 128
  role             = aws_iam_role.basic_lambda_role.arn
  runtime          = "python3.9"
  timeout          = 3
  architectures    = ["arm64"]
  environment {
    variables = {
      MQTT_BATCH  = "batch-listener"
      MQTT_ID     = "uploader_callsign"
      MQTT_PREFIX = "listener"
    }
  }
  tags = {
    Name = "sns-to-mqtt"
  }

  vpc_config {
    security_group_ids = [
      "sg-05f795128b295c504",
    ]
    subnet_ids = [
      aws_subnet.private["us-east-1b"].id
    ]
  }

}

resource "aws_lambda_permission" "sns_to_mqtt_listener" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.sns_to_mqtt_listener.arn
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.listener_telem.arn
}

resource "aws_sns_topic_subscription" "sns_to_mqtt_listener" {
  topic_arn = aws_sns_topic.listener_telem.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.sns_to_mqtt_listener.arn
}