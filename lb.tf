# Shared load balancer
resource "aws_lb" "ws" {
  name               = "ws"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.lb.id]
  subnets            = values(aws_subnet.public)[*].id

  enable_deletion_protection = true

  ip_address_type    = "dualstack"

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

resource "aws_lb_listener" "lb" {
  load_balancer_arn = aws_lb.ws.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = aws_acm_certificate_validation.CertificateManagerCertificate.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ws.arn
  }
}

resource "aws_lb_listener_rule" "tawhiri" {
  listener_arn = aws_lb_listener.lb.arn
  priority     = 2

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.tawhiri.arn
  }

  condition {
    host_header {
      values = ["tawhiri.v2.sondehub.org"]
    }
  }
}