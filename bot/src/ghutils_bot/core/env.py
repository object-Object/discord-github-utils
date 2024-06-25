from pydantic import SecretStr
from pydantic_settings import BaseSettings


class EnvSettings(BaseSettings):
    model_config = {
        "env_file": ".env",
    }

    token: SecretStr

    commit: str = "Unknown"
    commit_date: str = "Unknown"
