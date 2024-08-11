from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
from githubkit import OAuthTokenAuthStrategy
from sqlalchemy import Engine
from sqlmodel import Field, SQLModel  # pyright: ignore[reportUnknownVariableType]

from .types import TZAwareDateTime


class UserGitHubTokens(SQLModel, table=True):
    user_id: int = Field(primary_key=True, sa_type=sa.BigInteger)

    token: str | None = Field(repr=False)
    expire_time: datetime | None = Field(sa_type=TZAwareDateTime)

    refresh_token: str | None = Field(repr=False)
    refresh_token_expire_time: datetime | None = Field(sa_type=TZAwareDateTime)

    @classmethod
    def from_auth(cls, user_id: int, auth: OAuthTokenAuthStrategy):
        return cls(
            user_id=user_id,
            token=auth.token,
            expire_time=auth.expire_time,
            refresh_token=auth.refresh_token,
            refresh_token_expire_time=auth.refresh_token_expire_time,
        )

    def refresh(self, auth: OAuthTokenAuthStrategy):
        self.token = auth.token
        self.expire_time = auth.expire_time
        self.refresh_token = auth.refresh_token
        self.refresh_token_expire_time = auth.refresh_token_expire_time

    def to_auth(self, client_id: str, client_secret: str):
        self._fix_timezones()
        return OAuthTokenAuthStrategy(
            client_id=client_id,
            client_secret=client_secret,
            token=self.token,
            expire_time=self.expire_time,
            refresh_token=self.refresh_token,
            refresh_token_expire_time=self.refresh_token_expire_time,
        )

    def is_refresh_expired(self):
        if not self.refresh_token_expire_time:
            return False

        # say it's expired if the expiry time is earlier than one minute in the future
        # (to hopefully avoid weird boundary conditions around expiry)
        self._fix_timezones()
        expire_time = self.refresh_token_expire_time
        one_minute_from_now = datetime.now(UTC) + timedelta(minutes=1)
        return expire_time <= one_minute_from_now

    def _fix_timezones(self):
        # TODO: this should really be a validator, but SQLModel doesn't run them :/
        # https://github.com/tiangolo/sqlmodel/issues/52
        if self.expire_time:
            self.expire_time = self.expire_time.replace(tzinfo=UTC)
        if self.refresh_token_expire_time:
            self.refresh_token_expire_time = self.refresh_token_expire_time.replace(
                tzinfo=UTC
            )


class UserLogin(SQLModel, table=True):
    user_id: int = Field(primary_key=True, sa_type=sa.BigInteger)
    login_id: str


def create_db_and_tables(engine: Engine):
    SQLModel.metadata.create_all(engine)
