resource "aws_secretsmanager_secret" "mqtt" {
  name = "MQTT"
}

resource "aws_secretsmanager_secret_version" "mqtt" {
  secret_id = aws_secretsmanager_secret.mqtt.id
  secret_string = jsonencode(
    {
      HOST            = join(",", local.websocket_host_addresses)
      HOST_MOS_FORMAT = join(" ", [for x in local.websocket_host_addresses : "${x}:1883"])
      PASSWORD        = random_password.mqtt.result
      USERNAME        = "write"
    }
  )
  lifecycle {
    ignore_changes = [ 
      secret_binary
     ]
  }
}

resource "random_password" "mqtt" {
  length  = 18
  special = false
  lifecycle {
    ignore_changes = [special, bcrypt_hash, result]
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
    ignore_changes = [secret_string, secret_binary]
  }
}