from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from github.AccessToken import AccessToken
from github.ApplicationOAuth import ApplicationOAuth
from github.Auth import AppUserAuth
from sqlalchemy import Engine
from sqlmodel import Field, SQLModel  # pyright: ignore[reportUnknownVariableType]

from .types import TZAwareDateTime


class UserGitHubTokens(SQLModel, table=True):
    user_id: int = Field(primary_key=True, sa_type=sa.BigInteger)
    token: str = Field(repr=False)
    expires_at: datetime | None = Field(sa_type=TZAwareDateTime)
    refresh_token: str | None = Field(repr=False)
    refresh_expires_at: datetime | None = Field(sa_type=TZAwareDateTime)

    @classmethod
    def from_token(cls, user_id: int, token: AccessToken):
        return cls(
            user_id=user_id,
            token=token.token,
            refresh_token=token.refresh_token,
            expires_at=token.expires_at,
            refresh_expires_at=token.refresh_expires_at,
        )

    def refresh(self, token: AppUserAuth | AccessToken):
        self.token = token.token
        self.expires_at = token.expires_at
        self.refresh_token = token.refresh_token
        self.refresh_expires_at = token.refresh_expires_at

    def get_token(self, oauth: ApplicationOAuth):
        now = datetime.now(UTC)

        attributes: dict[str, Any] = {
            "access_token": self.token,
            "scope": "",
            "token_type": "bearer",
        }

        if self.refresh_token:
            attributes["refresh_token"] = self.refresh_token

        if (expires_in := self.expires_in(now)) is not None:
            attributes["expires_in"] = expires_in

        if (refresh_expires_in := self.refresh_expires_in(now)) is not None:
            attributes["refresh_token_expires_in"] = refresh_expires_in

        token = AccessToken(
            requester=oauth._requester,  # pyright: ignore[reportPrivateUsage]
            headers={},
            attributes=attributes,
            completed=False,
        )
        token._created = now  # pyright: ignore[reportPrivateUsage]
        return token

    # TODO: probably just get rid of SQLModel and use SA directly. this is stupid.
    # https://github.com/tiangolo/sqlmodel/issues/52#issuecomment-1311987732
    def expires_in(self, now: datetime):
        if self.expires_at:
            return int((self.expires_at.replace(tzinfo=UTC) - now).total_seconds())

    def refresh_expires_in(self, now: datetime):
        if self.refresh_expires_at:
            return int(
                (self.refresh_expires_at.replace(tzinfo=UTC) - now).total_seconds()
            )

    def is_refresh_expired(self):
        if not self.refresh_expires_at:
            return False
        return self.refresh_expires_at.replace(tzinfo=UTC) <= datetime.now(UTC)


class UserLogin(SQLModel, table=True):
    user_id: int = Field(primary_key=True, sa_type=sa.BigInteger)
    login_id: str


def create_db_and_tables(engine: Engine):
    SQLModel.metadata.create_all(engine)
