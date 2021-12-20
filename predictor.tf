resource "aws_iam_role" "predict_updater" {
  path                 = "/service-role/"
  name                 = "predict-updater"
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


resource "aws_iam_role_policy" "predict_updater" {
  name   = "predict_updater"
  role   = aws_iam_role.predict_updater.name
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
        },
        {
            "Effect": "Allow",
            "Action": "sqs:*",
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": "s3:*",
            "Resource": "*"
        }
    ]
}
EOF
}


resource "aws_lambda_function" "predict_updater" {
  function_name                  = "predict_updater"
  handler                        = "predict_updater.predict"
  s3_bucket                      = aws_s3_bucket_object.lambda.bucket
  s3_key                         = aws_s3_bucket_object.lambda.key
  source_code_hash               = data.archive_file.lambda.output_base64sha256
  publish                        = true
  memory_size                    = 1024
  role                           = aws_iam_role.predict_updater.arn
  runtime                        = "python3.9"
  architectures                  = ["arm64"]
  timeout                        = 300
  reserved_concurrent_executions = 1
  environment {
    variables = {
      "ES" = aws_route53_record.es.fqdn
    }
  }
}


resource "aws_cloudwatch_event_rule" "predict_updater" {
  name        = "predict_updater"
  description = "predict_updater"

  schedule_expression = "rate(1 minute)"
}

resource "aws_cloudwatch_event_target" "predict_updater" {
  rule      = aws_cloudwatch_event_rule.predict_updater.name
  target_id = "SendToLambda"
  arn       = aws_lambda_function.predict_updater.arn
}

resource "aws_lambda_permission" "predict_updater" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.predict_updater.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.predict_updater.arn
}

resource "aws_apigatewayv2_route" "predictions" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /predictions"
  target             = "integrations/${aws_apigatewayv2_integration.predictions.id}"
}

resource "aws_apigatewayv2_route" "reverse_predictions" {
  api_id             = aws_apigatewayv2_api.main.id
  api_key_required   = false
  authorization_type = "NONE"
  route_key          = "GET /predictions/reverse"
  target             = "integrations/${aws_apigatewayv2_integration.reverse_predictions.id}"
}

resource "aws_apigatewayv2_integration" "predictions" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.predictions.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "reverse_predictions" {
  api_id                 = aws_apigatewayv2_api.main.id
  connection_type        = "INTERNET"
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.reverse_predictions.arn
  timeout_milliseconds   = 30000
  payload_format_version = "2.0"
}

resource "aws_lambda_function" "predictions" {
  function_name    = "predictions"
  handler          = "predict.predict"
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
resource "aws_lambda_permission" "predictions" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.predictions.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/predictions"
}


resource "aws_lambda_function" "reverse_predictions" {
  function_name    = "reverse-predictions"
  handler          = "reverse_predict.predict"
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
resource "aws_lambda_permission" "reverse_predictions" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.reverse_predictions.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:${data.aws_caller_identity.current.account_id}:${aws_apigatewayv2_api.main.id}/*/*/predictions/reverse"
}




resource "aws_ecs_task_definition" "tawhiri" {
  family = "tawhiri"
  container_definitions = jsonencode(
    [
      {
        command = [
          "/root/.local/bin/gunicorn",
          "-b",
          "0.0.0.0:8000",
          "--workers=20",
          "--timeout=30",
          "--keep-alive=65",
          "--threads=1",
          "tawhiri.api:app"
        ]
        dependsOn = [
          {
            containerName = "downloader"
            condition     = "SUCCESS"
          }
        ]
        cpu         = 0
        environment = []
        essential   = true
        image       = "${data.aws_caller_identity.current.account_id}.dkr.ecr.us-east-1.amazonaws.com/tawhiri:latest"
        logConfiguration = {
          logDriver = "awslogs"
          options = {
            awslogs-group         = "/ecs/tawhiri"
            awslogs-region        = "us-east-1"
            awslogs-stream-prefix = "ecs"
          }
        }
        mountPoints = [
          {
            containerPath = "/srv"
            sourceVolume  = "srv"
          },
          {
            containerPath = "/srv/tawhiri-datasets"
            sourceVolume  = "downloader"
          }
        ]
        name = "tawhiri"
        portMappings = [
          {
            containerPort = 8000
            hostPort      = 8000
            protocol      = "tcp"
          },
        ]
        volumesFrom = []
      },
      {
        cpu = 0
        environment = [
          {
            name  = "TZ"
            value = "UTC"
          }
        ]
        essential = false
        image     = "${data.aws_caller_identity.current.account_id}.dkr.ecr.us-east-1.amazonaws.com/tawhiri-downloader:latest"
        logConfiguration = {
          logDriver = "awslogs"
          options = {
            awslogs-group         = "/ecs/tawhiri"
            awslogs-region        = "us-east-1"
            awslogs-stream-prefix = "ecs"
          }
        }
        mountPoints = [
          {
            containerPath = "/srv/tawhiri-datasets"
            sourceVolume  = "downloader"
          },
        ]
        name        = "downloader"
        volumesFrom = []
      },
    ]
  )
  cpu                = "512"
  execution_role_arn = aws_iam_role.ecs_execution.arn
  memory             = "1024"
  network_mode       = "awsvpc"
  requires_compatibilities = [
    "FARGATE",
  ]
  tags          = {}
  task_role_arn = aws_iam_role.ecs_execution.arn



  volume {
    name = "downloader"
  }

  volume {
    name = "srv"

    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.tawhiri.id
      root_directory     = "/srv"
      transit_encryption = "DISABLED"

      authorization_config {
        iam = "DISABLED"
      }
    }
  }
  lifecycle {
    ignore_changes = [volume] # terraform has a bug that doesn't correctly deal with root_directory because I don't know why - so we ignore it
  }
}

resource "aws_ecs_task_definition" "tawhiri_ruaumoko" {
  family = "tawhiri-ruaumoko"
  container_definitions = jsonencode(
    [
      {
        cpu = 0
        entryPoint = [
          "/root/.local/bin/ruaumoko-download",
        ]
        environment = []
        essential   = true
        image       = "${data.aws_caller_identity.current.account_id}.dkr.ecr.us-east-1.amazonaws.com/tawhiri:latest"
        logConfiguration = {
          logDriver = "awslogs"
          options = {
            awslogs-group         = "/ecs/tawhiri-ruaumoko"
            awslogs-region        = "us-east-1"
            awslogs-stream-prefix = "ecs"
          }
        }
        mountPoints = [
          {
            containerPath = "/srv"
            sourceVolume  = "srv"
          },
        ]
        name         = "ruaumoko"
        portMappings = []
        volumesFrom  = []
      },
    ]
  )
  cpu                = "1024"
  execution_role_arn = "arn:aws:iam::143841941773:role/ecsTaskExecutionRole"
  memory             = "2048"
  network_mode       = "awsvpc"
  requires_compatibilities = [
    "FARGATE",
  ]
  tags          = {}
  task_role_arn = "arn:aws:iam::143841941773:role/ecsTaskExecutionRole"


  volume {
    name = "srv"

    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.tawhiri.id
      root_directory     = "srv"
      transit_encryption = "DISABLED"

      authorization_config {
        iam = "DISABLED"
      }
    }
  }
}



resource "aws_efs_file_system" "tawhiri" {
  tags = {
    Name = "Tawhiri"
  }
  lifecycle_policy {
    transition_to_ia = "AFTER_7_DAYS"
  }
}

resource "aws_ecr_repository" "tawhiri" {
  name                 = "tawhiri"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}
resource "aws_ecr_repository" "tawhiri_downloader" {
  name                 = "tawhiri-downloader"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecs_cluster" "tawhiri" {
  name               = "Tawhiri"
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]
}


resource "aws_lb_target_group" "tawhiri" {
  name        = "tawhiri"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"
  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 10
    matcher             = "200"
    path                = "/api/datasetcheck"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }
}

resource "aws_ecs_service" "tawhiri" {
  name                              = "tawhiri"
  cluster                           = aws_ecs_cluster.tawhiri.id
  task_definition                   = aws_ecs_task_definition.tawhiri.arn
  enable_ecs_managed_tags           = true
  health_check_grace_period_seconds = 600
  iam_role                          = "aws-service-role"
  launch_type                       = "FARGATE"
  platform_version                  = "LATEST"
  desired_count                     = 1

  load_balancer {
    container_name   = "tawhiri"
    container_port   = 8000
    target_group_arn = aws_lb_target_group.tawhiri.arn
  }

  lifecycle {
    ignore_changes = [desired_count, task_definition]
  }

  network_configuration {
    assign_public_ip = true
    security_groups = [
      aws_security_group.tawhiri_efs.id,
      aws_security_group.tawhiri.id
    ]
    subnets = [aws_subnet.public["us-east-1b"].id]
  }
}


resource "aws_appautoscaling_target" "tawhiri" {
  service_namespace  = "ecs"
  scalable_dimension = "ecs:service:DesiredCount"
  resource_id        = "service/Tawhiri/tawhiri"
  min_capacity       = 1
  max_capacity       = 5
}

resource "aws_appautoscaling_policy" "tawhiri" {
  name               = "cpu"
  service_namespace  = aws_appautoscaling_target.tawhiri.service_namespace
  scalable_dimension = aws_appautoscaling_target.tawhiri.scalable_dimension
  resource_id        = aws_appautoscaling_target.tawhiri.resource_id
  policy_type        = "TargetTrackingScaling"

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }

    target_value       = 80
    scale_in_cooldown  = 120
    scale_out_cooldown = 120
  }
}

resource "aws_security_group" "tawhiri_efs" {
  name = "tawhiri-efs"
  ingress = [
    {
      from_port        = 2049
      to_port          = 2049
      protocol         = "tcp"
      cidr_blocks      = []
      ipv6_cidr_blocks = []
      description      = ""
      prefix_list_ids  = []
      self             = true
      security_groups  = [aws_vpc.main.default_security_group_id]
    }
  ]
  egress = [
    {
      from_port        = 0
      to_port          = 0
      protocol         = "-1"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
      description      = ""
      prefix_list_ids  = []
      self             = false
      security_groups  = []
    }
  ]
  vpc_id = aws_vpc.main.id

  lifecycle {
    ignore_changes = [description, name]
  }

}

resource "aws_security_group" "tawhiri" {
  name = "tawhiri"
  ingress = [
    {
      from_port        = 8000
      to_port          = 8000
      protocol         = "tcp"
      cidr_blocks      = []
      ipv6_cidr_blocks = []
      description      = ""
      prefix_list_ids  = []
      self             = true
      security_groups  = [aws_security_group.tawhiri_alb.id, aws_security_group.lb.id]
    }
  ]
  egress = [
    {
      from_port        = 0
      to_port          = 0
      protocol         = "-1"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
      description      = ""
      prefix_list_ids  = []
      self             = false
      security_groups  = []
    }
  ]
  vpc_id = aws_vpc.main.id

  lifecycle {
    ignore_changes = [description, name]
  }

}


resource "aws_security_group" "tawhiri_alb" {
  name = "tawhiri-alb"
  egress = [
    {
      from_port        = 0
      to_port          = 0
      protocol         = "-1"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
      description      = ""
      prefix_list_ids  = []
      self             = false
      security_groups  = []
    }
  ]
  ingress = [
    {
      from_port        = 443
      to_port          = 443
      protocol         = "tcp"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
      description      = ""
      prefix_list_ids  = []
      self             = false
      security_groups  = []
    }
  ]
  vpc_id = aws_vpc.main.id

  lifecycle {
    ignore_changes = [description, name]
  }

}



resource "aws_route53_record" "tawhiri_A" {
  name = "tawhiri"
  type = "A"
  alias {
    name                   = "dualstack.${aws_lb.ws.dns_name}."
    zone_id                = aws_lb.ws.zone_id
    evaluate_target_health = true
  }
  zone_id = aws_route53_zone.Route53HostedZone.zone_id
}

resource "aws_route53_record" "tawhiri_AAAA" {
  name = "tawhiri"
  type = "AAAA"
  alias {
    name                   = "dualstack.${aws_lb.ws.dns_name}."
    zone_id                = aws_lb.ws.zone_id
    evaluate_target_health = true
  }
  zone_id = aws_route53_zone.Route53HostedZone.zone_id
}

resource "aws_iam_role" "predictor_update_trigger_lambda" {
  path                 = "/service-role/"
  assume_role_policy   = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF
  max_session_duration = 3600
}

resource "aws_iam_role_policy" "predictor_update_trigger_lambda" {
  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "ecs:UpdateService",
            "Resource": "*"
        },
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
        }
    ]
}
EOF
  role   = aws_iam_role.predictor_update_trigger_lambda.name
}

resource "aws_lambda_function" "predictor_update_trigger_lambda" {
  function_name    = "tawhiri-updater"
  handler          = "tawhiri_updater.handler"
  s3_bucket        = aws_s3_bucket_object.lambda.bucket
  s3_key           = aws_s3_bucket_object.lambda.key
  source_code_hash = data.archive_file.lambda.output_base64sha256
  publish          = true
  memory_size      = 128
  role             = aws_iam_role.predictor_update_trigger_lambda.arn
  runtime          = "python3.9"
  timeout          = 3
}

resource "aws_lambda_permission" "predictor_update_trigger_lambda" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.predictor_update_trigger_lambda.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = "arn:aws:sns:us-east-1:123901341784:NewGFSObject"
}

resource "aws_sns_topic_subscription" "predictor_update_trigger_lambda" {
  topic_arn = "arn:aws:sns:us-east-1:123901341784:NewGFSObject"
  protocol  = "lambda"
  endpoint  = aws_lambda_function.predictor_update_trigger_lambda.arn
}

# sns subscription