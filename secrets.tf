resource "aws_secretsmanager_secret" "mqtt" {
  name = "MQTT"
}

resource "aws_secretsmanager_secret_version" "mqtt" {
  secret_id = aws_secretsmanager_secret.mqtt.id
  secret_string = jsonencode(
    {
      HOST     = join(",", local.websocket_host_addresses)
      PASSWORD = random_password.mqtt.result
      USERNAME = "write"
    }
  )
}

resource "random_password" "mqtt" {
  length  = 18
  special = false
  lifecycle {
    ignore_changes = [special]
  }
}

resource "aws_secretsmanager_secret" "radiosondy" {
  name = "RADIOSONDY"
}

resource "aws_secretsmanager_secret_version" "radiosondy" {
  secret_id = aws_secretsmanager_secret.radiosondy.id
  secret_string = jsonencode(
    {
      API_KEY = ""
    }
  )
  lifecycle {
    ignore_changes = [secret_string]
  }
}