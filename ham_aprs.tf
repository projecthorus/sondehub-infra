
resource "aws_ecs_task_definition" "aprsgw" {
  family = "aprsgw"
  runtime_platform {
    cpu_architecture = "ARM64"
  }
  container_definitions = jsonencode(
    [
      {
        cpu = 0
        "environment" : [
          { "name" : "AWS_REGION", "value" : "us-east-1" },
          { "name" : "AWS_DEFAULT_REGION", "value" : "us-east-1" },
          { "name" : "CALLSIGN", "value" : "VK3FUR" },
          { "name" : "SNS", "value" : aws_sns_topic.ham_telem.arn }
        ],
        essential = true
        image     = "${data.aws_caller_identity.current.account_id}.dkr.ecr.us-east-1.amazonaws.com/aprsgw:latest"
        logConfiguration = {
          logDriver = "awslogs"
          options = {
            awslogs-group         = "/ecs/aprsgw"
            awslogs-region        = "us-east-1"
            awslogs-stream-prefix = "ecs"
          }
        }
        mountPoints  = []
        name         = "aprsgw"
        portMappings = []
        ulimits      = []
        volumesFrom  = []
      },
    ]
  )
  cpu                = "256"
  execution_role_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/aprsgw"
  memory             = "512"
  network_mode       = "awsvpc"
  requires_compatibilities = [
    "FARGATE",
  ]
  tags          = {}
  task_role_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/aprsgw"
}

resource "aws_iam_role" "aprsgw" {
  name                 = "aprsgw"
  description          = "Allows EC2 instances to call AWS services on your behalf."
  assume_role_policy   = data.aws_iam_policy_document.ecs_task_assume_role_policy.json
  max_session_duration = 3600
}



resource "aws_iam_role_policy_attachment" "aprsgw" {
  role       = aws_iam_role.aprsgw.id
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "aprsgw" {
  statement {
    resources = ["*"]
    actions   = ["sns:Publish"]
  }

  statement {
    resources = [
      aws_secretsmanager_secret.mqtt.arn,
      aws_secretsmanager_secret.radiosondy.arn,
    ]

    actions = ["secretsmanager:GetSecretValue"]
  }
}

resource "aws_iam_role_policy" "aprsgw" {
  name = "aprsgw"
  role = aws_iam_role.aprsgw.id

  policy = data.aws_iam_policy_document.aprsgw.json
}

resource "aws_ecs_cluster" "aprsgw" {
  name = "aprsgw"
}


resource "aws_ecs_cluster_capacity_providers" "aprsgw" {
  cluster_name = aws_ecs_cluster.aprsgw.name

  capacity_providers = ["FARGATE"]
}


resource "aws_ecs_service" "aprsgw" {
  name                    = "aprsgw"
  cluster                 = aws_ecs_cluster.aprsgw.id
  task_definition         = aws_ecs_task_definition.aprsgw.arn
  enable_ecs_managed_tags = true
  launch_type             = "FARGATE"
  platform_version        = "LATEST"
  desired_count           = 1


  network_configuration {
    assign_public_ip = true
    security_groups  = []
    subnets          = [aws_subnet.public["us-east-1b"].id]
  }
}