terraform {
  backend "s3" {
    bucket = "sondehub-terraform"
    key    = "sondehub-main"
    region = "us-east-1"
  }
}
provider "aws" {
  region = "us-east-1"
}

locals {
  domain_name = "v2.sondehub.org"
}
data "aws_caller_identity" "current" {}



resource "aws_iam_role" "basic_lambda_role" {
  path                 = "/service-role/"
  name                 = "sonde-api-to-iot-core-role-z9zes3f5"
  assume_role_policy   = data.aws_iam_policy_document.lambda_assume_role_policy.json
  max_session_duration = 3600
}


data "aws_iam_policy_document" "basic_lambda_role" {
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
    resources = ["arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/*"]

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

resource "aws_iam_role_policy" "basic_lambda_role" {
  policy = data.aws_iam_policy_document.basic_lambda_role.json
  role   = aws_iam_role.basic_lambda_role.name
}



resource "aws_route53_zone" "Route53HostedZone" {
  name = "${local.domain_name}."
}

resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.CertificateManagerCertificate.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = aws_route53_zone.Route53HostedZone.zone_id
}
resource "aws_acm_certificate_validation" "CertificateManagerCertificate" {
  certificate_arn         = aws_acm_certificate.CertificateManagerCertificate.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}
resource "aws_acm_certificate" "CertificateManagerCertificate" {
  domain_name = local.domain_name
  subject_alternative_names = [
    "*.${local.domain_name}"
  ]
  validation_method = "DNS"
}


resource "aws_acm_certificate" "CertificateManagerCertificate_root" {
  domain_name = local.domain_name
  subject_alternative_names = [
    "*.${local.domain_name}",
    "sondehub.org",
    "*.sondehub.org"
  ]
  validation_method = "DNS"
}

data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "lambda/"
  output_path = "${path.module}/build/lambda.zip"
}

resource "aws_s3_bucket" "lambda_functions" {
}

resource "aws_s3_bucket_object" "lambda" {
  bucket = aws_s3_bucket.lambda_functions.bucket
  key    = "lambda.zip"
  source = data.archive_file.lambda.output_path
  etag   = data.archive_file.lambda.output_md5
}