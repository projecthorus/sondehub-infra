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

resource "aws_lambda_function" "sign_socket" {
  function_name    = "sign-websocket"
  handler          = "sign_websocket.lambda_handler"
  s3_bucket        = aws_s3_bucket_object.lambda.bucket
  s3_key           = aws_s3_bucket_object.lambda.key
  source_code_hash = data.archive_file.lambda.output_base64sha256
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


resource "aws_ecr_repository" "wsproxy" {
  name                 = "wsproxy"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}


// Subnet that is used to make discovery simple for the main ws server
resource "aws_subnet" "ws_main" {
  map_public_ip_on_launch = false
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "172.31.134.0/28"

  tags = {
    Name = "wsmain"
  }
}

resource "aws_route_table_association" "ws_main" {
  subnet_id      = aws_subnet.ws_main.id
  route_table_id = aws_route_table.main.id
}

// so we need to ensure there is only as handful of IP addresses avaliable in the subnet, so we assign all the IPs to ENIs
resource "aws_network_interface" "ws_pad" {
  count     = 9
  subnet_id = aws_subnet.ws_main.id

  description = "Do not delete. Padding to limit addresses"
}

# resource "aws_ecs_task_definition" "ws_reader" {
#   family = "ws-reader"
#   container_definitions = jsonencode(
#     [
#       {
#         command = [
#           "s3",
#           "sync",
#           "s3://sondehub-ws-config/",
#           "/config/",
#         ]
#         cpu         = 0
#         environment = []
#         essential   = false
#         image       = "amazon/aws-cli"
#         logConfiguration = {
#           logDriver = "awslogs"
#           options = {
#             awslogs-group         = "/ecs/ws"
#             awslogs-region        = "us-east-1"
#             awslogs-stream-prefix = "ecs"
#           }
#         }
#         mountPoints = [
#           {
#             containerPath = "/config"
#             sourceVolume  = "config"
#           },
#         ]
#         name         = "config"
#         portMappings = []
#         volumesFrom  = []
#       },
#       {
#         command = []
#         cpu     = 0
#         dependsOn = [
#           {
#             condition     = "SUCCESS"
#             containerName = "config"
#           },
#           {
#             condition     = "SUCCESS"
#             containerName = "config-move"
#           },
#         ]
#         environment = []
#         essential   = true
#         image       = "${data.aws_caller_identity.current.account_id}.dkr.ecr.us-east-1.amazonaws.com/wsproxy:latest"
#         logConfiguration = {
#           logDriver = "awslogs"
#           options = {
#             awslogs-group         = "/ecs/ws"
#             awslogs-region        = "us-east-1"
#             awslogs-stream-prefix = "ecs"
#           }
#         }
#         mountPoints = [
#           {
#             containerPath = "/mosquitto/config"
#             sourceVolume  = "config"
#           },
#         ]
#         name = "mqtt"
#         portMappings = [
#           {
#             containerPort = 8080
#             hostPort      = 8080
#             protocol      = "tcp"
#           },
#           {
#             containerPort = 8883
#             hostPort      = 8883
#             protocol      = "tcp"
#           },
#         ]
#         ulimits = [
#           {
#             hardLimit = 50000
#             name      = "nofile"
#             softLimit = 30000
#           },
#         ]
#         volumesFrom = []
#       },
#       {
#         command = [
#           "cp",
#           "/config/mosquitto-reader.conf",
#           "/config/mosquitto.conf",
#         ]
#         cpu = 0
#         dependsOn = [
#           {
#             condition     = "SUCCESS"
#             containerName = "config"
#           },
#         ]
#         environment = []
#         essential   = false
#         image       = "alpine"
#         # logConfiguration = {
#         #   logDriver = "awslogs"
#         #   options = {
#         #     awslogs-group         = "/ecs/ws-reader"
#         #     awslogs-region        = "us-east-1"
#         #     awslogs-stream-prefix = "ecs"
#         #   }
#         # }
#         mountPoints = [
#           {
#             containerPath = "/config"
#             sourceVolume  = "config"
#           },
#         ]
#         name         = "config-move"
#         portMappings = []
#         volumesFrom  = []
#       },
#     ]
#   )
#   cpu                = "256"
#   execution_role_arn = aws_iam_role.ecs_execution.arn
#   memory             = "512"
#   network_mode       = "awsvpc"
#   requires_compatibilities = [
#     "FARGATE",
#   ]

#   tags          = {}
#   task_role_arn = "arn:aws:iam::143841941773:role/ws"


#   volume {
#     name = "config"
#   }
# }

resource "aws_ecs_task_definition" "ws_reader_ec2" {
  family = "ws_reader_ec2"
  container_definitions = jsonencode(
    [
      {
        command = [
          "s3",
          "sync",
          "s3://sondehub-ws-config/",
          "/config/",
        ]
        cpu         = 0
        environment = []
        essential   = false
        image       = "amazon/aws-cli"
        logConfiguration = {
          logDriver = "awslogs"
          options = {
            awslogs-group         = "/ecs/ws"
            awslogs-region        = "us-east-1"
            awslogs-stream-prefix = "ecs"
          }
        }
        mountPoints = [
          {
            containerPath = "/config"
            sourceVolume  = "config"
          },
        ]
        name         = "config"
        portMappings = []
        volumesFrom  = []
      },
      {
        command = []
        cpu     = 0
        dependsOn = [
          {
            condition     = "SUCCESS"
            containerName = "config"
          },
          {
            condition     = "SUCCESS"
            containerName = "config-move"
          },
        ]
        environment = []
        essential   = true
        image       = "eclipse-mosquitto:latest"
        # logConfiguration = {
        #   logDriver = "awslogs"
        #   options = {
        #     awslogs-group         = "/ecs/ws"
        #     awslogs-region        = "us-east-1"
        #     awslogs-stream-prefix = "ecs"
        #   }
        # }
        mountPoints = [
          {
            containerPath = "/mosquitto/config"
            sourceVolume  = "config"
          },
        ]
        name = "mqtt"
        portMappings = [
          {
            containerPort = 8080
            hostPort      = 80
            protocol      = "tcp"
          },
        ]
        ulimits = [
          {
            hardLimit = 50000
            name      = "nofile"
            softLimit = 30000
          },
        ]
        volumesFrom = []
      },
      {
        command = [
          "cp",
          "/config/mosquitto-reader.conf",
          "/config/mosquitto.conf",
        ]
        cpu = 0
        dependsOn = [
          {
            condition     = "SUCCESS"
            containerName = "config"
          },
        ]
        environment = []
        essential   = false
        image       = "alpine"
        logConfiguration = {
          logDriver = "awslogs"
          options = {
            awslogs-group         = "/ecs/ws-reader"
            awslogs-region        = "us-east-1"
            awslogs-stream-prefix = "ecs"
          }
        }
        mountPoints = [
          {
            containerPath = "/config"
            sourceVolume  = "config"
          },
        ]
        name         = "config-move"
        portMappings = []
        volumesFrom  = []
      },
    ]
  )
  cpu                = "512"
  execution_role_arn = aws_iam_role.ecs_execution.arn
  memory             = "400"
  network_mode       = "bridge"
  requires_compatibilities = [
    "EC2",
  ]

  tags          = {}
  task_role_arn = "arn:aws:iam::143841941773:role/ws"


  volume {
    name = "config"
  }
}

resource "aws_ecs_task_definition" "ws" {
  family = "ws"
  container_definitions = jsonencode(
    [
      {
        command = [
          "s3",
          "sync",
          "s3://sondehub-ws-config/",
          "/config/",
        ]
        cpu         = 0
        environment = []
        essential   = false
        image       = "amazon/aws-cli"
        logConfiguration = {
          logDriver = "awslogs"
          options = {
            awslogs-group         = "/ecs/ws"
            awslogs-region        = "us-east-1"
            awslogs-stream-prefix = "ecs"
          }
        }
        mountPoints = [
          {
            containerPath = "/config"
            sourceVolume  = "config"
          },
        ]
        name         = "config"
        portMappings = []
        volumesFrom  = []
      },
      {
        cpu = 0
        dependsOn = [
          {
            condition     = "SUCCESS"
            containerName = "config"
          },
        ]
        environment = []
        essential   = true
        image       = "eclipse-mosquitto:2-openssl"
        # logConfiguration = {
        #   logDriver = "awslogs"
        #   options = {
        #     awslogs-group         = "/ecs/ws"
        #     awslogs-region        = "us-east-1"
        #     awslogs-stream-prefix = "ecs"
        #   }
        # }
        mountPoints = [
          {
            containerPath = "/mosquitto/config"
            sourceVolume  = "config"
          },
        ]
        name = "mqtt"
        portMappings = [
          {
            containerPort = 8080
            hostPort      = 8080
            protocol      = "tcp"
          },
          {
            containerPort = 8883
            hostPort      = 8883
            protocol      = "tcp"
          },
          {
            containerPort = 1883
            hostPort      = 1883
            protocol      = "tcp"
          },
        ]
        ulimits = [
          {
            hardLimit = 50000
            name      = "nofile"
            softLimit = 30000
          },
        ]
        volumesFrom = []
      },
    ]
  )
  cpu                = "256"
  execution_role_arn = "arn:aws:iam::143841941773:role/ws"
  memory             = "512"
  network_mode       = "awsvpc"
  requires_compatibilities = [
    "FARGATE",
  ]
  tags          = {}
  task_role_arn = "arn:aws:iam::143841941773:role/ws"


  volume {
    name = "config"
  }
}

resource "aws_ecs_cluster" "ws" {
  name               = "ws"
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]
}

resource "aws_lb_target_group" "ws" {
  name        = "ws"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"
  health_check {
    enabled             = true
    healthy_threshold   = 5
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }
}
resource "aws_lb_target_group" "ws_reader" {
  name        = "ws-reader"
  port        = 8061
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"
  health_check {
    enabled             = true
    healthy_threshold   = 5
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }
}

# resource "aws_ecs_service" "ws_reader" {
#   name                              = "ws-reader"
#   cluster                           = aws_ecs_cluster.ws.id
#   task_definition                   = aws_ecs_task_definition.ws_reader.arn
#   enable_ecs_managed_tags           = true
#   health_check_grace_period_seconds = 60
#   iam_role                          = "aws-service-role"
#   launch_type                       = "FARGATE"
#   platform_version                  = "LATEST"
#   desired_count                     = 0

#   load_balancer {
#     container_name   = "mqtt"
#     container_port   = 8080
#     target_group_arn = aws_lb_target_group.ws_reader.arn
#   }

#   lifecycle {
#     ignore_changes = [desired_count]
#   }

#   network_configuration {
#     assign_public_ip = true
#     security_groups = [
#       aws_security_group.ws_reader.id
#     ]
#     subnets = values(aws_subnet.public)[*].id
#   }
# }

resource "aws_ecs_service" "ws_reader_ec2" {
  name                    = "ws-reader-ec2"
  cluster                 = aws_ecs_cluster.ws.id
  task_definition         = aws_ecs_task_definition.ws_reader_ec2.arn
  enable_ecs_managed_tags = true
  launch_type             = "EC2"
  desired_count           = 6
  placement_constraints {
    type = "distinctInstance"
  }
}

resource "aws_ecs_service" "ws_writer" {
  name                              = "ws-writer"
  cluster                           = aws_ecs_cluster.ws.id
  task_definition                   = aws_ecs_task_definition.ws.arn
  enable_ecs_managed_tags           = true
  health_check_grace_period_seconds = 60
  iam_role                          = "aws-service-role"
  launch_type                       = "FARGATE"
  platform_version                  = "LATEST"
  desired_count                     = 1

  load_balancer {
    container_name   = "mqtt"
    container_port   = 8080
    target_group_arn = aws_lb_target_group.ws.arn
  }

  lifecycle {
    ignore_changes = [desired_count]
  }

  network_configuration {
    assign_public_ip = true
    security_groups = [
      aws_security_group.ws_writer.id
    ]
    subnets = [aws_subnet.ws_main.id]
  }
}

resource "aws_security_group" "ws_reader" {
  ingress = [
    {
      from_port        = 0
      to_port          = 0
      protocol         = "-1"
      cidr_blocks      = []
      ipv6_cidr_blocks = []
      description      = ""
      prefix_list_ids  = []
      self             = true
      security_groups  = [aws_security_group.ws_writer.id, aws_security_group.lb.id]
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


resource "aws_security_group" "ws_writer" {

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

resource "aws_security_group_rule" "ws_writer_reader" {
  security_group_id        = aws_security_group.ws_writer.id
  type                     = "ingress"
  from_port                = 0
  to_port                  = 0
  protocol                 = "-1"
  description              = ""
  source_security_group_id = aws_security_group.ws_reader.id
}
resource "aws_security_group_rule" "ws_writer_lb" {
  security_group_id        = aws_security_group.ws_writer.id
  type                     = "ingress"
  from_port                = 0
  to_port                  = 0
  protocol                 = "-1"
  description              = ""
  source_security_group_id = aws_security_group.lb.id
}

resource "aws_security_group_rule" "ws_writer_lightsail_lb" {
  security_group_id = aws_security_group.ws_writer.id
  type              = "ingress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  description       = ""
  cidr_blocks       = ["172.26.0.0/16"]
}

# resource "aws_s3_bucket" "ws" {
#   bucket = "sondehub-ws-config"
#   acl    = "private"
#   versioning {
#     enabled = true
#   }
#   lifecycle {
#     ignore_changes = [bucket]
#   }
# }

resource "aws_iam_role" "ecs_execution" {
  name                 = "ecsTaskExecutionRole"
  assume_role_policy   = <<EOF
{
  "Version": "2008-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
  max_session_duration = 3600
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.id
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "efs" {
  name = "EFS"
  role = aws_iam_role.ecs_execution.id

  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": "elasticfilesystem:*",
            "Resource": "*"
        }
    ]
}
EOF
}

resource "aws_iam_role_policy" "ssm" {
  name = "SSM"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode(
    {
      Statement = [
        {
          Action = [
            "ssmmessages:CreateControlChannel",
            "ssmmessages:CreateDataChannel",
            "ssmmessages:OpenControlChannel",
            "ssmmessages:OpenDataChannel",
          ]
          Effect   = "Allow"
          Resource = "*"
        }
      ]
      Version = "2012-10-17"
    }
  )
}

resource "aws_iam_role_policy" "kms" {
  name = "kms"
  role = aws_iam_role.ecs_execution.id

  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": "kms:*",
            "Resource": "*"
        }
    ]
}
EOF
}

resource "aws_iam_role" "ws" {
  name                 = "ws"
  description          = "Allows EC2 instances to call AWS services on your behalf."
  assume_role_policy   = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
  max_session_duration = 3600
}

resource "aws_iam_role_policy_attachment" "ws" {
  role       = aws_iam_role.ws.id
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "s3_config" {
  name = "s3-config"
  role = aws_iam_role.ws.id

  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "s3:GetObjectAcl",
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::sondehub-ws-config",
                "arn:aws:s3:::sondehub-ws-config/*"
            ]
        }
    ]
}
EOF
}

# resource "aws_appautoscaling_target" "ws_reader" {
#   service_namespace  = "ecs"
#   scalable_dimension = "ecs:service:DesiredCount"
#   resource_id        = "service/ws/ws-reader"
#   min_capacity       = 0
#   max_capacity       = 0
# }

# resource "aws_appautoscaling_policy" "ws_reader" {
#   name               = "ws-reader-tt"
#   service_namespace  = aws_appautoscaling_target.ws_reader.service_namespace
#   scalable_dimension = aws_appautoscaling_target.ws_reader.scalable_dimension
#   resource_id        = aws_appautoscaling_target.ws_reader.resource_id
#   policy_type        = "TargetTrackingScaling"

#   target_tracking_scaling_policy_configuration {
#     predefined_metric_specification {
#       predefined_metric_type = "ECSServiceAverageCPUUtilization"
#     }

#     target_value       = 60
#     scale_in_cooldown  = 200
#     scale_out_cooldown = 200
#   }
# }

# TODO
# s3 config bucket



resource "aws_route53_record" "ws_reader_CNAME" {
  name    = "ws-reader"
  type    = "CNAME"
  ttl     = 300
  zone_id = aws_route53_zone.Route53HostedZone.zone_id
  records = ["e31a53851c58b6410708e31423860d7d-1304003304.us-east-1.elb.amazonaws.com."]
}

resource "aws_route53_record" "ws_A" {
  name = "ws"
  type = "A"
  alias {
    name                   = "dualstack.${aws_lb.ws.dns_name}."
    zone_id                = aws_lb.ws.zone_id
    evaluate_target_health = true
  }
  zone_id = aws_route53_zone.Route53HostedZone.zone_id
}

resource "aws_route53_record" "ws_AAAA" {
  name = "ws"
  type = "AAAA"
  alias {
    name                   = "dualstack.${aws_lb.ws.dns_name}."
    zone_id                = aws_lb.ws.zone_id
    evaluate_target_health = true
  }
  zone_id = aws_route53_zone.Route53HostedZone.zone_id
}