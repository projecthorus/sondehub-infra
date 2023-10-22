
resource "aws_vpc" "main" {
  cidr_block                       = "172.31.0.0/16"
  assign_generated_ipv6_cidr_block = true
}

resource "aws_egress_only_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

locals {
  private_subnets = {
    "us-east-1a" = ["172.31.128.0/24", cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 13)],
    "us-east-1b" = ["172.31.131.0/24", cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 14)],
    "us-east-1c" = ["172.31.130.0/24", cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 15)],
    "us-east-1d" = ["172.31.133.0/24", cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 16)],
    "us-east-1e" = ["172.31.129.0/24", cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 17)],
    "us-east-1f" = ["172.31.132.0/24", cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 18)]
  }
  private_v6 = {
    "us-east-1a" = cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 7),
    "us-east-1b" = cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 8),
    "us-east-1c" = cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 9),
    "us-east-1d" = cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 10),
    "us-east-1e" = cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 11),
    "us-east-1f" = cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 12)
  }
  public_subnets = {
    "us-east-1a" = ["172.31.80.0/20", cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 19)],
    "us-east-1b" = ["172.31.16.0/20", cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 20)],
    "us-east-1c" = ["172.31.32.0/20", cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 21)],
    "us-east-1d" = ["172.31.0.0/20", cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 22)],
    "us-east-1e" = ["172.31.48.0/20", cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 23)],
    "us-east-1f" = ["172.31.64.0/20", cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 24)]
  }
  public_v6 = {
    "us-east-1a" = cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 1),
    "us-east-1b" = cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 2),
    "us-east-1c" = cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 3),
    "us-east-1d" = cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 4),
    "us-east-1e" = cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 5),
    "us-east-1f" = cidrsubnet(aws_vpc.main.ipv6_cidr_block, 8, 6)
  }
}
resource "aws_subnet" "private" {
  for_each = local.private_subnets

  map_public_ip_on_launch         = false
  vpc_id                          = aws_vpc.main.id
  cidr_block                      = each.value[0]
  ipv6_cidr_block                 = each.value[1]
  assign_ipv6_address_on_creation = true
  tags = {
    Name = "${each.key} - private"
  }
}

resource "aws_subnet" "public" {
  for_each = local.public_subnets

  map_public_ip_on_launch         = false
  vpc_id                          = aws_vpc.main.id
  cidr_block                      = each.value[0]
  ipv6_cidr_block                 = each.value[1]
  assign_ipv6_address_on_creation = true

  tags = {
    Name = "${each.key} - public"
  }
}

resource "aws_subnet" "public_v6_only" {
  for_each = local.public_v6

  availability_zone                              = each.key
  enable_resource_name_dns_aaaa_record_on_launch = true
  assign_ipv6_address_on_creation                = true
  vpc_id                                         = aws_vpc.main.id
  ipv6_native                                    = true
  ipv6_cidr_block                                = each.value
  tags = {
    Name = "${each.key} - public v6 only"
  }

}

resource "aws_subnet" "private_v6_only" {
  for_each = local.private_v6

  availability_zone                              = each.key
  enable_resource_name_dns_aaaa_record_on_launch = true
  assign_ipv6_address_on_creation                = true
  vpc_id                                         = aws_vpc.main.id
  ipv6_native                                    = true
  ipv6_cidr_block                                = each.value
  tags = {
    Name = "${each.key} - private v6 only"
  }

}

resource "aws_route_table" "main" {
  vpc_id = aws_vpc.main.id
}

resource "aws_route_table" "public_v6" {
  vpc_id = aws_vpc.main.id
}

resource "aws_route_table_association" "public" {
  for_each       = local.public_subnets
  subnet_id      = aws_subnet.public[each.key].id
  route_table_id = aws_route_table.public_v6.id
}

resource "aws_route_table_association" "public_v6_only" {
  for_each       = local.public_v6
  subnet_id      = aws_subnet.public_v6_only[each.key].id
  route_table_id = aws_route_table.public_v6.id
}

resource "aws_route_table_association" "private_v6_only" {
  for_each       = local.private_v6
  subnet_id      = aws_subnet.private_v6_only[each.key].id
  route_table_id = aws_route_table.main.id
}

resource "aws_route_table_association" "private" {
  for_each       = local.private_subnets
  subnet_id      = aws_subnet.private[each.key].id
  route_table_id = aws_route_table.main.id
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id
}

resource "aws_route" "main6" {
  route_table_id              = aws_route_table.main.id
  destination_ipv6_cidr_block = "::/0"
  egress_only_gateway_id      = aws_egress_only_internet_gateway.main.id
}

resource "aws_route" "main" {
  route_table_id         = aws_route_table.main.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.gw.id
}

resource "aws_route" "public" {
  route_table_id         = aws_route_table.public_v6.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.gw.id
}

resource "aws_route" "public_v6" {
  route_table_id              = aws_route_table.public_v6.id
  destination_ipv6_cidr_block = "::/0"
  gateway_id                  = aws_internet_gateway.gw.id
}

resource "aws_security_group" "vpcendpoint" {
  name        = "vpcendpoint"
  description = "vpcendpoint"
  ingress = [
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
  egress = [
    {
      from_port        = 0
      to_port          = 0
      protocol         = "-1"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
      security_groups  = []
      description      = ""
      prefix_list_ids  = []
      self             = false
    }
  ]
  vpc_id = aws_vpc.main.id

}


resource "aws_vpc_endpoint" "secretsmanager" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.us-east-1.secretsmanager"
  vpc_endpoint_type = "Interface"

  security_group_ids = [
    aws_security_group.vpcendpoint.id,
  ]

  private_dns_enabled = true
}