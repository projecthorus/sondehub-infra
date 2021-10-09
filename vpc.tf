
resource "aws_vpc" "main" {
  cidr_block = "172.31.0.0/16"
  assign_generated_ipv6_cidr_block = true
}

resource "aws_egress_only_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
}

locals {
  private_subnets = {
    "us-east-1a"= "172.31.128.0/24",
    "us-east-1b"= "172.31.131.0/24",
    "us-east-1c"= "172.31.130.0/24",
    "us-east-1d"= "172.31.133.0/24",
    "us-east-1e"= "172.31.129.0/24",
    "us-east-1f"= "172.31.132.0/24"
  }
  public_subnets = {
    "us-east-1a"= "172.31.80.0/20",
    "us-east-1b"= "172.31.16.0/20",
    "us-east-1c"= "172.31.32.0/20",
    "us-east-1d"= "172.31.0.0/20",
    "us-east-1e"= "172.31.48.0/20",
    "us-east-1f"= "172.31.64.0/20"
  }
}
resource "aws_subnet" "private" {
  for_each = local.private_subnets

  map_public_ip_on_launch = false
  vpc_id     = aws_vpc.main.id
  cidr_block = each.value
  
  tags = {
    Name = "${each.key} - private"
  }
}

resource "aws_subnet" "public" {
  for_each = local.public_subnets

  map_public_ip_on_launch = false
  vpc_id     = aws_vpc.main.id
  cidr_block = each.value
  
  tags = {
    Name = "${each.key} - public"
  }
}

resource "aws_route_table" "main" {
  vpc_id = aws_vpc.main.id
}
resource "aws_route_table_association" "public" {
  for_each = local.public_subnets
  subnet_id      = aws_subnet.public[each.key].id
  route_table_id = aws_route_table.main.id
}
resource "aws_route_table_association" "private" {
  for_each = local.private_subnets
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
  route_table_id              = aws_route_table.main.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id      = aws_internet_gateway.gw.id
}