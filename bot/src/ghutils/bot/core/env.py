from __future__ import annotations

import functools

from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings


class GHUtilsEnv(BaseSettings):
    model_config = {
        "hide_input_in_errors": True,
        "env_file": ".env",
        "env_nested_delimiter": "__",
    }

    token: SecretStr
    db_url: str

    commit: str = "Unknown"
    commit_date: str = "Unknown"

    github: GitHub

    class GitHub(BaseModel):
        client_id: str
        client_secret: SecretStr
        redirect_uri: str

    @staticmethod
    @functools.cache
    def get():
        return GHUtilsEnv.model_validate({})
