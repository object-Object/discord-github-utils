from __future__ import annotations

import functools
import logging
from typing import Literal

from github import Github
from pydantic import BaseModel, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class GHUtilsEnv(BaseSettings):
    model_config = {
        "hide_input_in_errors": True,
        "env_file": ".env",
        "env_nested_delimiter": "__",
    }

    token: SecretStr
    db_url: str = Field("")
    environment: Literal["dev", "prod"]

    commit: str = "Unknown"
    commit_date: str = "Unknown"

    github: GitHub

    @staticmethod
    @functools.cache
    def get():
        return GHUtilsEnv.model_validate({})

    @model_validator(mode="after")
    def _post_root(self):
        if not self.db_url:
            match self.environment:
                case "dev":
                    logger.warning("DB_URL not set, using local SQLite DB")
                    self.db_url = "sqlite:///db.sqlite"
                case "prod":
                    raise ValueError("DB_URL is required but not set")
        return self

    class GitHub(BaseModel):
        client_id: str
        client_secret: SecretStr
        redirect_uri: str

        def get_oauth_application(self):
            return Github().get_oauth_application(
                client_id=self.client_id,
                client_secret=self.client_secret.get_secret_value(),
            )
