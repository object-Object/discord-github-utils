from __future__ import annotations

import functools
import logging
from pathlib import Path
from typing import Literal

from github import Github
from github.Auth import AppAuth
from pydantic import BaseModel, Field, PrivateAttr, SecretStr, model_validator
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
        app_id: int
        client_id: str
        client_secret: SecretStr
        private_key_path: Path
        redirect_uri: str
        default_installation_id: int

        _private_key: SecretStr = PrivateAttr()

        @property
        def private_key(self):
            return self._private_key

        def get_oauth_application(self):
            return Github().get_oauth_application(
                client_id=self.client_id,
                client_secret=self.client_secret.get_secret_value(),
            )

        def get_login_url(self, state: str):
            return self.get_oauth_application().get_login_url(
                redirect_uri=self.redirect_uri,
                state=state,
            )

        # if a user isn't logged in, authenticate using a specific installation
        # to get a higher ratelimit than unauthenticated requests
        def get_default_installation_auth(self):
            return AppAuth(
                app_id=self.app_id,
                private_key=self.private_key.get_secret_value(),
            ).get_installation_auth(
                installation_id=self.default_installation_id,
            )

        @model_validator(mode="after")
        def _post_root(self):
            self._private_key = SecretStr(self.private_key_path.read_text("utf-8"))
            return self
