from __future__ import annotations

import logging
import re

from discord import Interaction
from discord.app_commands import Transform, Transformer
from discord.app_commands.models import Choice
from githubkit import Response
from githubkit.exception import GitHubException, RequestFailed
from githubkit.rest import FullRepository, PrivateUser, PublicUser

from ghutils.core.bot import GHUtilsBot
from ghutils.core.types import LoginState
from ghutils.db.config import get_configs
from ghutils.utils.github import RepositoryName, gh_request

logger = logging.getLogger(__name__)


REPO_URL_PATTERN = re.compile(r"(?:https?://)?github.com/(?P<value>[\w-]+/[\w-]+)")

USER_URL_PATTERN = re.compile(r"(?:https?://)?github.com/(?P<value>[\w-]+)")


class RepositoryTransformer(Transformer):
    async def transform(self, interaction: Interaction, value: str) -> FullRepository:
        if match := REPO_URL_PATTERN.match(value):
            value = match["value"]

        repo = RepositoryName.parse(value)
        async with GHUtilsBot.github_app_of(interaction) as (github, _):
            try:
                return await gh_request(
                    github.rest.repos.async_get(repo.owner, repo.repo)
                )
            except GitHubException as e:
                match e:
                    case RequestFailed(response=Response(status_code=404)):
                        raise ValueError("Repository not found")
                    case _:
                        logger.warning(e)
                        raise ValueError(f"Failed to get repository: {e}")

    async def autocomplete(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        interaction: Interaction,
        value: str,
    ) -> list[Choice[str]]:
        value = value.strip()
        if value:
            if match := REPO_URL_PATTERN.match(value):
                value = match["value"]
            query = f"{value} in:name fork:true"
        else:
            with GHUtilsBot.db_session_of(interaction) as session:
                configs = get_configs(session, interaction)
                if repo := configs.default_repo:
                    return [Choice(name=str(repo), value=str(repo))]
            return []

        async with GHUtilsBot.github_app_of(interaction) as (github, state):
            if state != LoginState.LOGGED_IN:
                return []

            try:
                result = await gh_request(
                    github.rest.search.async_repos(
                        q=query,
                        per_page=25,
                    )
                )
            except RequestFailed:
                return []
            except GitHubException as e:
                logger.warning(e)
                return []

            return [
                Choice(name=repo.full_name, value=repo.full_name)
                for repo in result.items
            ]


class UserTransformer(Transformer):
    async def transform(
        self,
        interaction: Interaction,
        value: str,
    ) -> PrivateUser | PublicUser:
        if match := USER_URL_PATTERN.match(value):
            value = match["value"]

        async with GHUtilsBot.github_app_of(interaction) as (github, _):
            try:
                return await gh_request(github.rest.users.async_get_by_username(value))
            except GitHubException as e:
                match e:
                    case RequestFailed(response=Response(status_code=404)):
                        raise ValueError("User not found")
                    case _:
                        logger.warning(e)
                        raise ValueError(f"Failed to get user: {e}")

    async def autocomplete(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        interaction: Interaction,
        value: str,
    ) -> list[Choice[str]]:
        async with GHUtilsBot.github_app_of(interaction) as (github, state):
            if state != LoginState.LOGGED_IN:
                return []

            # If no value given, assume the user wants their own profile
            if not value:
                user = await gh_request(github.rest.users.async_get_authenticated())
                return [Choice(name=user.login, value=user.login)]

            if match := USER_URL_PATTERN.match(value):
                value = match["value"]

            try:
                result = await gh_request(
                    github.rest.search.async_users(
                        q=value,
                        per_page=25,
                    )
                )
            except RequestFailed:
                return []
            except GitHubException as e:
                logger.warning(e)
                return []

            return [Choice(name=user.login, value=user.login) for user in result.items]


RepositoryOption = Transform[FullRepository, RepositoryTransformer]

UserOption = Transform[PrivateUser | PublicUser, UserTransformer]
