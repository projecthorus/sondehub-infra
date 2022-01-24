# manages the short codes


resource "aws_lambda_function" "redirect" {
  function_name = "sondehub-redirect"
  handler       = "redirect.handler"
  s3_bucket     = aws_s3_bucket_object.lambda.bucket
  s3_key        = aws_s3_bucket_object.lambda.key
  publish       = true
  memory_size   = 128
  role          = aws_iam_role.basic_lambda_role.arn
  runtime       = "python3.9"
  timeout       = 3
}



resource "aws_route53_record" "testing_A" {
  name = "testing"
  type = "A"
  alias {
    name                   = aws_cloudfront_distribution.testing.domain_name
    zone_id                = aws_cloudfront_distribution.testing.hosted_zone_id
    evaluate_target_health = false
  }
  zone_id = aws_route53_zone.Route53HostedZone.zone_id
}

resource "aws_route53_record" "testing_AAAA" {
  name = "testing"
  type = "AAAA"
  alias {
    name                   = aws_cloudfront_distribution.testing.domain_name
    zone_id                = aws_cloudfront_distribution.testing.hosted_zone_id
    evaluate_target_health = false
  }
  zone_id = aws_route53_zone.Route53HostedZone.zone_id
}


resource "aws_route53_record" "root_A" {
  name            = ""
  allow_overwrite = true
  type            = "A"
  alias {
    name                   = aws_cloudfront_distribution.sondehub.domain_name
    zone_id                = aws_cloudfront_distribution.sondehub.hosted_zone_id
    evaluate_target_health = false
  }
  zone_id = "Z0756308IVLVF48G6G1S"
}

resource "aws_route53_record" "root_AAAA" {
  name            = ""
  allow_overwrite = true
  type            = "AAAA"
  alias {
    name                   = aws_cloudfront_distribution.sondehub.domain_name
    zone_id                = aws_cloudfront_distribution.sondehub.hosted_zone_id
    evaluate_target_health = false
  }
  zone_id = "Z0756308IVLVF48G6G1S"
}

resource "aws_route53_record" "predict_A" {
  name = "predict"
  type = "A"
  alias {
    name                   = aws_cloudfront_distribution.predict.domain_name
    zone_id                = aws_cloudfront_distribution.predict.hosted_zone_id
    evaluate_target_health = false
  }
  zone_id = "Z0756308IVLVF48G6G1S"
}

resource "aws_route53_record" "predict_AAAA" {
  name = "predict"
  type = "AAAA"
  alias {
    name                   = aws_cloudfront_distribution.predict.domain_name
    zone_id                = aws_cloudfront_distribution.predict.hosted_zone_id
    evaluate_target_health = false
  }
  zone_id = "Z0756308IVLVF48G6G1S"
}

resource "aws_route53_record" "tracker_A" {
  name = "tracker"
  type = "A"
  alias {
    name                   = aws_cloudfront_distribution.sondehub.domain_name
    zone_id                = aws_cloudfront_distribution.sondehub.hosted_zone_id
    evaluate_target_health = false
  }
  zone_id = "Z0756308IVLVF48G6G1S"
}

resource "aws_route53_record" "tracker_AAAA" {
  name = "tracker"
  type = "AAAA"
  alias {
    name                   = aws_cloudfront_distribution.sondehub.domain_name
    zone_id                = aws_cloudfront_distribution.sondehub.hosted_zone_id
    evaluate_target_health = false
  }
  zone_id = "Z0756308IVLVF48G6G1S"
}

resource "aws_route53_record" "www_A" {
  name = "www"
  type = "A"
  alias {
    name                   = aws_cloudfront_distribution.sondehub.domain_name
    zone_id                = aws_cloudfront_distribution.sondehub.hosted_zone_id
    evaluate_target_health = false
  }
  zone_id = "Z0756308IVLVF48G6G1S"
}

resource "aws_route53_record" "www_AAAA" {
  name = "www"
  type = "AAAA"
  alias {
    name                   = aws_cloudfront_distribution.sondehub.domain_name
    zone_id                = aws_cloudfront_distribution.sondehub.hosted_zone_id
    evaluate_target_health = false
  }
  zone_id = "Z0756308IVLVF48G6G1S"
}

resource "aws_route53_record" "v2_A" {
  name            = ""
  allow_overwrite = true
  type            = "A"
  alias {
    name                   = aws_cloudfront_distribution.sondehub.domain_name
    zone_id                = aws_cloudfront_distribution.sondehub.hosted_zone_id
    evaluate_target_health = false
  }
  zone_id = aws_route53_zone.Route53HostedZone.zone_id
}

resource "aws_route53_record" "v2_AAAA" {
  name            = ""
  allow_overwrite = true
  type            = "AAAA"
  alias {
    name                   = aws_cloudfront_distribution.sondehub.domain_name
    zone_id                = aws_cloudfront_distribution.sondehub.hosted_zone_id
    evaluate_target_health = false
  }
  zone_id = aws_route53_zone.Route53HostedZone.zone_id
}

resource "aws_route53_record" "api_raw" {
  name = "api-raw"
  type = "CNAME"
  ttl  = 300
  records = [
    aws_apigatewayv2_domain_name.ApiGatewayV2DomainName.domain_name_configuration[0].target_domain_name
  ]
  zone_id = aws_route53_zone.Route53HostedZone.zone_id
}

resource "aws_route53_record" "api_A" {
  name = "api"
  type = "A"
  alias {
    name                   = aws_cloudfront_distribution.api.domain_name
    zone_id                = aws_cloudfront_distribution.api.hosted_zone_id
    evaluate_target_health = false
  }
  zone_id = aws_route53_zone.Route53HostedZone.zone_id
}

resource "aws_route53_record" "api_AAAA" {
  name = "api"
  type = "AAAA"
  alias {
    name                   = aws_cloudfront_distribution.api.domain_name
    zone_id                = aws_cloudfront_distribution.api.hosted_zone_id
    evaluate_target_health = false
  }
  zone_id = aws_route53_zone.Route53HostedZone.zone_id
}


resource "aws_cloudfront_distribution" "sondehub" {
  aliases = [
    local.domain_name,
    "sondehub.org",
    "tracker.sondehub.org",
    "www.sondehub.org"
  ]
  default_root_object = "index.html"
  origin {
    custom_origin_config {
      http_port                = 80
      https_port               = 443
      origin_keepalive_timeout = 5
      origin_protocol_policy   = "https-only"
      origin_read_timeout      = 30
      origin_ssl_protocols = [
        "TLSv1",
        "TLSv1.1",
        "TLSv1.2"
      ]
    }
    domain_name = aws_cloudfront_distribution.card.domain_name
    origin_id   = "card"
    origin_path = ""
  }
  origin {
    domain_name = aws_s3_bucket.v2.bucket_regional_domain_name
    origin_id   = "S3-${local.domain_name}"
    origin_path = ""
  }
  default_cache_behavior {
    allowed_methods = ["GET", "HEAD", "OPTIONS"]
    cached_methods = [
      "HEAD",
      "GET"
    ]
    compress    = true
    default_ttl = 120
    forwarded_values {
      cookies {
        forward = "none"
      }
      query_string = false
    }
    lambda_function_association {
      event_type = "viewer-request"
      lambda_arn = aws_lambda_function.redirect.qualified_arn
    }
    max_ttl                = 120
    min_ttl                = 120
    smooth_streaming       = false
    target_origin_id       = "S3-${local.domain_name}"
    viewer_protocol_policy = "redirect-to-https"
  }
  ordered_cache_behavior {

    allowed_methods = ["GET", "HEAD"]
    cached_methods = [
      "HEAD",
      "GET"
    ]
    compress    = true
    default_ttl = 120
    forwarded_values {
      cookies {
        forward = "none"
      }
      query_string = false
    }
    max_ttl                = 120
    min_ttl                = 120
    path_pattern           = "card/*"
    smooth_streaming       = false
    target_origin_id       = "card"
    viewer_protocol_policy = "redirect-to-https"
  }
  ordered_cache_behavior {
    allowed_methods = ["GET", "HEAD", "OPTIONS"]
    cached_methods = [
      "HEAD",
      "GET"
    ]
    compress    = true
    default_ttl = 120
    forwarded_values {
      cookies {
        forward = "none"
      }
      query_string = false
    }
    max_ttl                = 120
    min_ttl                = 120
    path_pattern           = "*.*"
    smooth_streaming       = false
    target_origin_id       = "S3-${local.domain_name}"
    viewer_protocol_policy = "redirect-to-https"
  }
  custom_error_response {
    error_caching_min_ttl = 10
    error_code            = 403
    response_code         = "200"
    response_page_path    = "/card/index.html"
  }
  custom_error_response {
    error_caching_min_ttl = 10
    error_code            = 404
    response_code         = "200"
    response_page_path    = "/card/index.html"
  }
  comment     = ""
  price_class = "PriceClass_All"
  enabled     = true
  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.CertificateManagerCertificate_root.arn
    minimum_protocol_version = "TLSv1.2_2019"
    ssl_support_method       = "sni-only"
  }
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  http_version    = "http2"
  is_ipv6_enabled = true
}

resource "aws_cloudfront_distribution" "testing" {
  aliases = [
    "testing.${local.domain_name}"
  ]
  default_root_object = "index.html"
  origin {
    domain_name = aws_s3_bucket.v2.bucket_regional_domain_name
    origin_id   = "S3-${local.domain_name}/testing"
    origin_path = "/testing"
  }
  default_cache_behavior {
    allowed_methods = ["GET", "HEAD"]
    cached_methods = [
      "HEAD",
      "GET"
    ]
    compress    = true
    default_ttl = 5
    forwarded_values {
      cookies {
        forward = "none"
      }
      query_string = false
    }
    max_ttl                = 5
    min_ttl                = 0
    smooth_streaming       = false
    target_origin_id       = "S3-${local.domain_name}/testing"
    viewer_protocol_policy = "redirect-to-https"
  }
  comment     = ""
  price_class = "PriceClass_All"
  enabled     = true
  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.CertificateManagerCertificate.certificate_arn
    minimum_protocol_version = "TLSv1.2_2021"
    ssl_support_method       = "sni-only"
  }
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  http_version    = "http2"
  is_ipv6_enabled = true
}

resource "aws_cloudfront_distribution" "card" {
  origin {
    domain_name = aws_s3_bucket.card.bucket_regional_domain_name
    origin_id   = aws_s3_bucket.card.bucket_regional_domain_name
    origin_path = ""
  }
  default_cache_behavior {
    allowed_methods = ["GET", "HEAD"]
    cached_methods = [
      "HEAD",
      "GET"
    ]
    compress    = false
    default_ttl = 120
    forwarded_values {
      cookies {
        forward = "none"
      }
      query_string = false
    }
    max_ttl                = 120
    min_ttl                = 120
    smooth_streaming       = false
    target_origin_id       = aws_s3_bucket.card.bucket_regional_domain_name
    viewer_protocol_policy = "redirect-to-https"
  }
  comment             = ""
  default_root_object = "index.html"
  price_class         = "PriceClass_100"
  enabled             = true
  viewer_certificate {
    cloudfront_default_certificate = true
    minimum_protocol_version       = "TLSv1"
  }
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  http_version    = "http2"
  is_ipv6_enabled = true
}

resource "aws_cloudfront_distribution" "predict" {
  aliases = [
    "predict.sondehub.org"
  ]
  origin {
    domain_name = aws_s3_bucket.predict.bucket_regional_domain_name
    origin_id   = aws_s3_bucket.predict.bucket_regional_domain_name
    origin_path = ""
  }
  default_root_object = "index.html"
  default_cache_behavior {
    allowed_methods = ["GET", "HEAD", "OPTIONS"]
    cached_methods = [
      "HEAD",
      "GET"
    ]
    compress    = true
    default_ttl = 120
    forwarded_values {
      cookies {
        forward = "none"
      }
      query_string = false
    }
    max_ttl                = 120
    min_ttl                = 120
    smooth_streaming       = false
    target_origin_id       = aws_s3_bucket.predict.bucket_regional_domain_name
    viewer_protocol_policy = "redirect-to-https"
  }
  comment     = ""
  price_class = "PriceClass_100"
  enabled     = true
  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.CertificateManagerCertificate_root.arn
    minimum_protocol_version = "TLSv1.2_2021"
    ssl_support_method       = "sni-only"
  }
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  http_version    = "http2"
  is_ipv6_enabled = true
}

resource "aws_cloudfront_distribution" "api" {
  aliases = [
    "api.${local.domain_name}"
  ]
  origin {
    custom_origin_config {
      http_port                = 80
      https_port               = 443
      origin_keepalive_timeout = 5
      origin_protocol_policy   = "https-only"
      origin_read_timeout      = 60
      origin_ssl_protocols = [
        "TLSv1.2"
      ]
    }
    domain_name = aws_apigatewayv2_domain_name.ApiGatewayV2DomainName.domain_name
    origin_id   = "Custom-api.${local.domain_name}"
    origin_path = ""
  }
  default_cache_behavior {
    allowed_methods = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods = [
      "HEAD",
      "GET"
    ]
    compress    = true
    default_ttl = 60
    forwarded_values {
      cookies {
        forward = "none"
      }
      headers = [
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers"
      ]
      query_string = true
    }
    max_ttl                = 120
    min_ttl                = 60
    smooth_streaming       = false
    target_origin_id       = "Custom-api.${local.domain_name}"
    viewer_protocol_policy = "allow-all"
  }
  ordered_cache_behavior {
    allowed_methods = ["GET", "HEAD"]
    cached_methods = [
      "HEAD",
      "GET"
    ]
    compress    = true
    default_ttl = 30
    forwarded_values {
      cookies {
        forward = "none"
      }
      headers = [
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers"
      ]
      query_string = true
    }
    max_ttl                = 30
    min_ttl                = 30
    path_pattern           = "predictions"
    smooth_streaming       = false
    target_origin_id       = "Custom-api.${local.domain_name}"
    viewer_protocol_policy = "redirect-to-https"
  }
  ordered_cache_behavior {
    allowed_methods = ["GET", "HEAD"]
    cached_methods = [
      "HEAD",
      "GET"
    ]
    compress    = true
    default_ttl = 300
    forwarded_values {
      cookies {
        forward = "none"
      }
      headers = [
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers"
      ]
      query_string = false
    }
    max_ttl                = 300
    min_ttl                = 300
    path_pattern           = "pledges"
    smooth_streaming       = false
    target_origin_id       = "Custom-api.${local.domain_name}"
    viewer_protocol_policy = "redirect-to-https"
  }
  ordered_cache_behavior {
    allowed_methods = ["GET", "HEAD", "OPTIONS"] 
    cached_methods = [
      "HEAD",
      "GET"
    ]
    compress    = true
    default_ttl = 300
    forwarded_values {
      cookies {
        forward = "none"
      }
      headers = [
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers"
      ]
      query_string = false
    }
    max_ttl                = 300
    min_ttl                = 300
    path_pattern           = "listener/stats"
    smooth_streaming       = false
    target_origin_id       = "Custom-api.${local.domain_name}"
    viewer_protocol_policy = "redirect-to-https"
  }
  comment     = ""
  price_class = "PriceClass_100"
  enabled     = true
  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.CertificateManagerCertificate.certificate_arn
    minimum_protocol_version = "TLSv1.2_2019"
    ssl_support_method       = "sni-only"
  }
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  http_version    = "http2"
  is_ipv6_enabled = true
}



resource "aws_s3_bucket" "v2" {
  bucket = local.domain_name
}

resource "aws_s3_bucket" "cf_logs" {
  bucket = "sondehub-cloudfront-logs"
}

resource "aws_s3_bucket" "history" {
  bucket = "sondehub-history"
  cors_rule {
    allowed_headers = [
      "*",
    ]
    allowed_methods = [
      "GET",
    ]
    allowed_origins = [
      "*",
    ]
    expose_headers  = []
    max_age_seconds = 0
  }
  website {
    index_document = "index.html"
  }
}

resource "aws_s3_bucket" "predict" {
  bucket = "sondehub-predict"
}

resource "aws_s3_bucket" "card" {
  bucket = "sondehub-v2-card"
}


resource "aws_s3_bucket_policy" "S3BucketPolicy" {
  bucket = aws_s3_bucket.v2.bucket
  policy = "{\"Version\":\"2012-10-17\",\"Id\":\"Policy1615627853229\",\"Statement\":[{\"Sid\":\"Stmt1615627852247\",\"Effect\":\"Allow\",\"Principal\":\"*\",\"Action\":\"s3:GetObject\",\"Resource\":\"arn:aws:s3:::${local.domain_name}/*\"}]}"
}

resource "aws_s3_bucket_policy" "S3BucketPolicy2" {
  bucket = aws_s3_bucket.history.bucket
  policy = "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"PublicRead\",\"Effect\":\"Allow\",\"Principal\":\"*\",\"Action\":[\"s3:GetObject\",\"s3:GetObjectVersion\",\"s3:ListBucket\",\"s3:GetObjectTorrent\"],\"Resource\":[\"arn:aws:s3:::sondehub-history/*\",\"arn:aws:s3:::sondehub-history\"]}]}"
}