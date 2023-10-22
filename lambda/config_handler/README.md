Helper class for getting config and secrets within SondeHub


## Example

```python
import config_handler

mqtt_password = config_handler.get("MQTT", "PASSWORD")
```

## Logic

1. Checks environment variable for "{TOPIC}_{PARAMETER}" if it exists return that value
2. If that doesn't exist then we perform a `SecretsManager.Client.get_secret_value(SecretId={TOPIC})`
3. We then `json.loads()` this value and return the respective value.