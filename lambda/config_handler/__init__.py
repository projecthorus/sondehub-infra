import os
import boto3
import json
import functools

@functools.lru_cache()
def get(topic: str, parameter: str, default=None) -> str:
    """
    Get's a configuration parameter.

    :param topic: The topic parameter (a logical grouping). When used with SecretsManager this is the secrets name
    :param parameter: The parameter to look up. When used with SecretsManager this is the key in the json config
    :param default: If the parameter isn't found return this value
    :returns: The config or secret value as a string
    :raises KeyError: raises a keyerror if the topic and parameter pair aren't found
    """

    # Try environment variables first
    try:
        return os.environ[f"{topic}_{parameter}"]
    except KeyError:
        pass

    # Try secrets manager
    sm = boto3.client('secretsmanager')
    try:
        secret_data = json.loads(sm.get_secret_value(SecretId=topic)['SecretString'])
        return secret_data[parameter]
    except (KeyError, sm.exceptions.ResourceNotFoundException):
        pass
    except:
        if default:
            return default
        raise
    
    if default:
        return default
    raise KeyError(f"Could not location a value for {topic} {parameter}")
    