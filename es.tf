

resource "aws_elasticsearch_domain" "ElasticsearchDomain" {
  domain_name           = "sondes-v2-7-9"
  elasticsearch_version = "OpenSearch_2.9"
  cluster_config {
    dedicated_master_count   = 3
    dedicated_master_enabled = false
    dedicated_master_type    = "t3.small.elasticsearch"
    instance_count           = 1
    instance_type            = "r6g.xlarge.elasticsearch"
    zone_awareness_enabled   = false
  }
  cognito_options {
    enabled          = true
    identity_pool_id = aws_cognito_identity_pool.CognitoIdentityPool.id
    role_arn         = aws_iam_role.IAMRole3.arn
    user_pool_id     = aws_cognito_user_pool.CognitoUserPool.id
  }
  domain_endpoint_options {
    enforce_https                   = true
    tls_security_policy             = "Policy-Min-TLS-1-2-2019-07"
    custom_endpoint                 = "es.v2.sondehub.org"
    custom_endpoint_certificate_arn = "arn:aws:acm:us-east-1:143841941773:certificate/a7da821c-bdbc-404b-aa12-bce28d86cdeb"
    custom_endpoint_enabled         = true
  }
  access_policies = <<EOF
    {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "*"
            },
            "Action": "es:*",
            "Resource": "arn:aws:es:us-east-1:${data.aws_caller_identity.current.account_id}:domain/sondes-v2*"
        }
    ]
}
EOF
  encrypt_at_rest {
    enabled    = true
    kms_key_id = data.aws_kms_key.es.arn
  }
  node_to_node_encryption {
    enabled = true
  }
  advanced_security_options {
    enabled = true
    master_user_options {
      master_user_arn = "arn:aws:iam::143841941773:role/es-admin"
    }
  }
  advanced_options = {
    "rest.action.multi.allow_explicit_index" = "true"
    "override_main_response_version"         = "true"
  }
  ebs_options {
    ebs_enabled = true
    volume_type = "gp3"
    volume_size = 200
    iops        = 3000
  }
  log_publishing_options {
    cloudwatch_log_group_arn = "arn:aws:logs:us-east-1:143841941773:log-group:/aws/aes/domains/sondes-v2/application-logs"
    enabled                  = true
    log_type                 = "ES_APPLICATION_LOGS"
  }
  log_publishing_options {
    cloudwatch_log_group_arn = "arn:aws:logs:us-east-1:143841941773:log-group:/aws/aes/domains/sondes-v2/index-logs"
    enabled                  = true
    log_type                 = "INDEX_SLOW_LOGS"
  }
  log_publishing_options {
    cloudwatch_log_group_arn = "arn:aws:logs:us-east-1:143841941773:log-group:/aws/aes/domains/sondes-v2/search-logs"
    enabled                  = true
    log_type                 = "SEARCH_SLOW_LOGS"
  }
  lifecycle {
    prevent_destroy = true
  }
}
data "aws_kms_key" "es" {
  key_id = "alias/aws/es"
}

resource "aws_cognito_identity_pool" "CognitoIdentityPool" {
  identity_pool_name               = "sondes"
  allow_unauthenticated_identities = false

  supported_login_providers = {
    "accounts.google.com" = "575970424139-vkk7scicbdd1igj04riqjh2bbs0oa6vj.apps.googleusercontent.com"
  }
  cognito_identity_providers {
    client_id               = aws_cognito_user_pool_client.CognitoUserPoolClient.id
    provider_name           = aws_cognito_user_pool.CognitoUserPool.endpoint
    server_side_token_check = false
  }

  cognito_identity_providers {
    client_id               = "4uvts41d75b2r2cmsdgff47pec"
    provider_name           = "cognito-idp.us-east-1.amazonaws.com/us-east-1_G4H7NMniM"
    server_side_token_check = false
  }
  cognito_identity_providers {
    client_id               = "7v892rnrta8ms785pl0aaqo8ke"
    provider_name           = "cognito-idp.us-east-1.amazonaws.com/us-east-1_G4H7NMniM"
    server_side_token_check = false
  }

  cognito_identity_providers {
    client_id     = "u3ggvo1spp1e6cffbietq7fbm"
    provider_name = "cognito-idp.us-east-1.amazonaws.com/us-east-1_G4H7NMniM"
  }
  cognito_identity_providers { // for the website
    client_id               = "21dpr4kth8lonk2rq803loh5oa"
    provider_name           = "cognito-idp.us-east-1.amazonaws.com/us-east-1_G4H7NMniM"
    server_side_token_check = false
  }

}

resource "aws_cognito_identity_pool_roles_attachment" "CognitoIdentityPoolRoleAttachment" {
  identity_pool_id = aws_cognito_identity_pool.CognitoIdentityPool.id
  roles = {
    authenticated   = aws_iam_role.auth_role.arn
    unauthenticated = aws_iam_role.unauth_role.arn
  }
  role_mapping {
    ambiguous_role_resolution = "AuthenticatedRole"
    identity_provider         = "cognito-idp.us-east-1.amazonaws.com/us-east-1_G4H7NMniM:4uvts41d75b2r2cmsdgff47pec"
    type                      = "Token"
  }
  role_mapping {
    ambiguous_role_resolution = "AuthenticatedRole"
    identity_provider         = "cognito-idp.us-east-1.amazonaws.com/us-east-1_G4H7NMniM:227g2bbcb2tqjfii1ipt2tj5m6"
    type                      = "Token"
  }

  role_mapping {
    ambiguous_role_resolution = "AuthenticatedRole"
    identity_provider         = "cognito-idp.us-east-1.amazonaws.com/us-east-1_G4H7NMniM:u3ggvo1spp1e6cffbietq7fbm"
    type                      = "Token"
  }
  role_mapping {
    ambiguous_role_resolution = "AuthenticatedRole"
    identity_provider         = "cognito-idp.us-east-1.amazonaws.com/us-east-1_G4H7NMniM:7v892rnrta8ms785pl0aaqo8ke"
    type                      = "Token"
  }
}

resource "aws_cognito_user_pool" "CognitoUserPool" {
  name = "sondes"
  password_policy {
    temporary_password_validity_days = 7
    minimum_length                   = 8
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = true
    require_uppercase                = true
  }

  schema {
    attribute_data_type      = "String"
    developer_only_attribute = false
    mutable                  = true
    name                     = "email"
    string_attribute_constraints {
      max_length = "2048"
      min_length = "0"
    }
    required = true
  }
  username_configuration {
    case_sensitive = false
  }

  auto_verified_attributes = [
    "email"
  ]
  alias_attributes = [
    "email",
    "preferred_username"
  ]
  sms_verification_message   = "Your verification code is {####}. "
  email_verification_message = "Your verification code is {####}. "
  email_verification_subject = "Your verification code"
  sms_authentication_message = "Your authentication code is {####}. "
  mfa_configuration          = "OFF"
  device_configuration {
    challenge_required_on_new_device      = false
    device_only_remembered_on_user_prompt = false
  }
  email_configuration {

  }
  admin_create_user_config {
    allow_admin_create_user_only = false
    invite_message_template {
      email_message = "Your username is {username} and temporary password is {####}. "
      email_subject = "Your temporary password"
      sms_message   = "Your username is {username} and temporary password is {####}. "
    }
  }
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }
}

resource "aws_cognito_user_pool_client" "CognitoUserPoolClient" {
  user_pool_id                         = aws_cognito_user_pool.CognitoUserPool.id
  name                                 = "AWSElasticsearch-sondes-v2-us-east-1-hiwdpmnjbuckpbwfhhx65mweee"
  refresh_token_validity               = 30
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes                 = ["email", "openid", "phone", "profile"]
  callback_urls                        = ["https://es.${local.domain_name}/_dashboards/app/home"]
  logout_urls                          = ["https://es.${local.domain_name}/_dashboards/app/home"]
  supported_identity_providers         = ["COGNITO", "Google"]
  explicit_auth_flows                  = ["ALLOW_CUSTOM_AUTH", "ALLOW_REFRESH_TOKEN_AUTH", "ALLOW_USER_SRP_AUTH"]

  access_token_validity = 60
  id_token_validity     = 60
  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }
}

resource "aws_cognito_user_pool_domain" "main" {
  domain          = "auth.${local.domain_name}"
  user_pool_id    = aws_cognito_user_pool.CognitoUserPool.id
  certificate_arn = aws_acm_certificate_validation.CertificateManagerCertificate.certificate_arn
}


resource "aws_route53_record" "auth" {
  for_each = toset(["A", "AAAA"])
  name     = "auth"
  type     = each.key
  alias {
    name                   = "${aws_cognito_user_pool_domain.main.cloudfront_distribution_arn}."
    zone_id                = "Z2FDTNDATAQYW2"
    evaluate_target_health = false
  }
  zone_id = aws_route53_zone.Route53HostedZone.zone_id
}

resource "aws_route53_record" "es" {
  name = "es"
  type = "CNAME"
  ttl  = 300
  records = [
    aws_elasticsearch_domain.ElasticsearchDomain.endpoint
  ]
  zone_id = aws_route53_zone.Route53HostedZone.zone_id
}


resource "aws_iam_role" "auth_role" {
  path                 = "/"
  name                 = "Cognito_sondesAuth_Role"
  assume_role_policy   = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {
            "Federated": "cognito-identity.amazonaws.com"
        },
        "Action": "sts:AssumeRoleWithWebIdentity",
        "Condition": {
            "StringEquals": {
                "cognito-identity.amazonaws.com:aud": "${aws_cognito_identity_pool.CognitoIdentityPool.id}"
            },
            "ForAnyValue:StringLike": {
                "cognito-identity.amazonaws.com:amr": "authenticated"
            }
        }
    }]
}
EOF
  max_session_duration = 3600
}

resource "aws_iam_role" "unauth_role" {
  path                 = "/"
  name                 = "Cognito_sondesUnauth_Role"
  assume_role_policy   = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {
            "Federated": "cognito-identity.amazonaws.com"
        },
        "Action": "sts:AssumeRoleWithWebIdentity",
        "Condition": {
            "StringEquals": {
                "cognito-identity.amazonaws.com:aud": "${aws_cognito_identity_pool.CognitoIdentityPool.id}"
            },
            "ForAnyValue:StringLike": {
                "cognito-identity.amazonaws.com:amr": "unauthenticated"
            }
        }
    }]
}
EOF
  max_session_duration = 3600
}

resource "aws_iam_role" "IAMRole3" {
  path                 = "/service-role/"
  name                 = "CognitoAccessForAmazonES"
  assume_role_policy   = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [{
        "Effect": "Allow",
        "Principal": {
            "Service": "es.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
    }]
}
EOF
  max_session_duration = 3600
}


resource "aws_iam_service_linked_role" "IAMServiceLinkedRole" {
  aws_service_name = "es.amazonaws.com"
}


resource "aws_iam_role_policy" "IAMPolicy" {
  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
               {
            "Effect": "Allow",
            "Action": "es:*",
            "Resource": "arn:aws:es:us-east-1:${data.aws_caller_identity.current.account_id}:domain/sondes-*"
        },
        {
            "Effect": "Allow",
            "Action": "es:*",
            "Resource": "arn:aws:es:us-east-1:${data.aws_caller_identity.current.account_id}:domain/sondes-*"
        }
    ]
}
EOF
  role   = aws_iam_role.auth_role.name
}

resource "aws_iam_role_policy" "IAMPolicy2" {
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "mobileanalytics:PutEvents",
        "cognito-sync:*"
      ],
      "Resource": [
        "*"
      ]
    }
  ]
}
EOF
  role   = aws_iam_role.unauth_role.name
}

resource "aws_iam_role_policy" "IAMPolicy3" {
  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "mobileanalytics:PutEvents",
        "cognito-sync:*",
        "cognito-identity:*"
      ],
      "Resource": [
        "*"
      ]
    }
  ]
}
EOF
  role   = aws_iam_role.auth_role.name
}

resource "aws_iam_role_policy" "IAMPolicy4" {
  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "execute-api:*"
            ],
            "Resource": [
                "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/amateur/flightdoc"
            ]
        }
    ]
}
EOF
  role   = aws_iam_role.auth_role.name
}