from __future__ import annotations

from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings


class EnvSettings(BaseSettings):
    model_config = {
        "hide_input_in_errors": True,
        "env_file": ".env",
        "env_nested_delimiter": "__",
    }

    token: SecretStr

    commit: str = "Unknown"
    commit_date: str = "Unknown"

    github: GitHubSettings


class GitHubSettings(BaseModel):
    client_id: str
    client_secret: SecretStr
    redirect_uri: str
