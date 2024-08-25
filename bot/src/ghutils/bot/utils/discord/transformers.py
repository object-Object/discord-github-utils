from __future__ import annotations

from discord import Interaction
from discord.app_commands import Transform, Transformer

from ghutils.bot.core.bot import GHUtilsBot
from ghutils.bot.core.types import LoginState

from ..github import Repository, gh_request


class RepositoryTransformer(Transformer):
    async def transform(self, interaction: Interaction, value: str):
        if result := Repository.parse(value):
            return result

        async with GHUtilsBot.github_app_of(interaction) as (github, state):
            if state != LoginState.LOGGED_IN:
                raise ValueError(
                    f"Value does not contain '/' and user is not logged in: {value}"
                )

            user = await gh_request(github.rest.users.async_get_authenticated())
            return Repository(owner=user.login, repo=value)


RepositoryParam = Transform[Repository, RepositoryTransformer]
