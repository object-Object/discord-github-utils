from __future__ import annotations

import logging
from typing import ClassVar, Literal, Self

from githubkit import AppInstallationAuthStrategy, OAuthAppAuthStrategy
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings as PydanticBaseSettings, SettingsConfigDict
from yarl import URL

from ghutils.bot.db.models import UserGitHubTokens

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

    def get_login_url(self, state: str):
        """https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-user-access-token-for-a-github-app#using-the-web-application-flow-to-generate-a-user-access-token"""
        return URL("https://github.com/login/oauth/authorize").with_query(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            state=state,
        )

    def get_oauth_app_auth(self):
        return OAuthAppAuthStrategy(
            client_id=self.client_id,
            client_secret=self.client_secret.get_secret_value(),
        )

    # if a user isn't logged in, authenticate using a specific installation
    # to get a higher ratelimit than unauthenticated requests
    def get_default_installation_auth(self):
        return AppInstallationAuthStrategy(
            app_id=self.app_id,
            private_key=self.private_key.get_secret_value(),
            installation_id=self.default_installation_id,
            client_id=self.client_id,
            client_secret=self.client_secret.get_secret_value(),
        )

    def get_user_auth(self, user_tokens: UserGitHubTokens):
        return user_tokens.to_auth(
            client_id=self.client_id,
            client_secret=self.client_secret.get_secret_value(),
        )


class GHUtilsEnv(BaseSettings):
    token: SecretStr
    db_url: str = Field("")
    environment: Literal["dev", "prod"]
    api_port: int = 5000

    commit: str = "Unknown"
    commit_date: str = "Unknown"

    github: GitHubSettings = Field(default_factory=GitHubSettings.get)
    """GitHub-related environment variables."""

    @property
    def gh(self):
        return self.github
