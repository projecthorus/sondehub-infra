# Shared load balancer
resource "aws_lb" "ws" {
  name               = "ws"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.lb.id]
  subnets            = values(aws_subnet.public)[*].id

  enable_deletion_protection = true

}

resource "aws_security_group" "lb" {
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

# TODO
# listener
# lsitener rules