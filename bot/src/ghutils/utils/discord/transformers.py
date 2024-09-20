from __future__ import annotations

from discord import Interaction
from discord.app_commands import Transform, Transformer

from ghutils.core.bot import GHUtilsBot
from ghutils.core.types import LoginState

from ..github import RepositoryName, gh_request


class RepositoryNameTransformer(Transformer):
    async def transform(self, interaction: Interaction, value: str):
        if result := RepositoryName.parse(value):
            return result

        async with GHUtilsBot.github_app_of(interaction) as (github, state):
            if state != LoginState.LOGGED_IN:
                raise ValueError(
                    f"Value does not contain '/' and user is not logged in: {value}"
                )

            user = await gh_request(github.rest.users.async_get_authenticated())
            return RepositoryName(owner=user.login, repo=value)


RepositoryNameOption = Transform[RepositoryName, RepositoryNameTransformer]
