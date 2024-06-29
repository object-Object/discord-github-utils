from __future__ import annotations

import logging
from typing import ClassVar, Literal, Self

from github import Github
from github.Auth import AppAuth
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings as PydanticBaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


SETTINGS_CONFIG = SettingsConfigDict(
    hide_input_in_errors=True,
    env_file=".env",
    secrets_dir="secrets",
    extra="ignore",
)


class BaseSettings(PydanticBaseSettings):
    model_config = SETTINGS_CONFIG

    __cached: ClassVar[Self | None] = None

    @classmethod
    def get(cls) -> Self:
        if cls.__cached is None:
            cls.__cached = cls.model_validate({})
        return cls.__cached


class GitHubSettings(BaseSettings, env_prefix="github__"):
    app_id: int
    client_id: str
    client_secret: SecretStr
    private_key: SecretStr
    redirect_uri: str
    default_installation_id: int

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


class GHUtilsEnv(BaseSettings):
    token: SecretStr
    db_url: str = Field("")
    environment: Literal["dev", "prod"]
    api_port: int = 5000

    commit: str = "Unknown"
    commit_date: str = "Unknown"

    github: GitHubSettings = Field(default_factory=GitHubSettings.get)
