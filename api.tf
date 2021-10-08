resource "aws_apigatewayv2_api" "main" {
  name                         = "sondehub-v2"
  disable_execute_api_endpoint = true
  api_key_selection_expression = "$request.header.x-api-key"
  protocol_type                = "HTTP"
  route_selection_expression   = "$request.method $request.path"

  cors_configuration {
    allow_credentials = false
    allow_headers = [
      "*",
    ]
    allow_methods = [
      "*",
    ]
    allow_origins = [
      "*",
    ]
    expose_headers = []
    max_age        = 0
  }

}

resource "aws_apigatewayv2_stage" "default" {
  name   = "$default"
  api_id = aws_apigatewayv2_api.main.id
  default_route_settings {
    detailed_metrics_enabled = false
  }
  auto_deploy = true
  lifecycle {
    ignore_changes = [deployment_id]
  }
}

resource "aws_iam_service_linked_role" "IAMServiceLinkedRole3" {
  aws_service_name = "ops.apigateway.amazonaws.com"
  description      = "The Service Linked Role is used by Amazon API Gateway."
}

resource "aws_apigatewayv2_api_mapping" "ApiGatewayV2ApiMapping" {
  api_id          = aws_apigatewayv2_api.main.id
  domain_name     = aws_apigatewayv2_domain_name.ApiGatewayV2DomainName.id
  stage           = "$default"
  api_mapping_key = ""
}

resource "aws_apigatewayv2_domain_name" "ApiGatewayV2DomainName" {
  domain_name = "api-raw.${local.domain_name}"
  domain_name_configuration {
    certificate_arn = aws_acm_certificate_validation.CertificateManagerCertificate.certificate_arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }
}