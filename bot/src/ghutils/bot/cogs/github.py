from __future__ import annotations

import uuid
from dataclasses import dataclass

from discord import Interaction, app_commands
from discord.app_commands import Group, Transform, Transformer
from discord.ext.commands import GroupCog
from discord.ui import Button, View

from ghutils.bot.core import GHUtilsCog
from ghutils.bot.core.bot import GHUtilsBot
from ghutils.bot.core.types import LoginResult
from ghutils.bot.db.models import UserGitHubTokens, UserLogin


@dataclass
class Repository:
    owner: str
    repo: str

    def __str__(self) -> str:
        return f"{self.owner}/{self.repo}"


class RepositoryTransformer(Transformer):
    async def transform(self, interaction: Interaction, value: str):
        if "/" in value:
            owner, repo = value.split("/")
            return Repository(owner=owner, repo=repo)

        bot = interaction.client
        assert isinstance(bot, GHUtilsBot)

        github, result = bot.get_github_app(interaction)
        if result != LoginResult.LOGGED_IN:
            raise ValueError(
                f"Value does not contain '/' and user is not logged in: {value}"
            )

        return Repository(owner=github.get_user().login, repo=value)


RepositoryParam = Transform[Repository, RepositoryTransformer]


@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
class GitHubCog(GHUtilsCog, GroupCog, group_name="gh"):
    """GitHub-related commands."""

    # /gh

    @app_commands.command()
    async def issue(self, interaction: Interaction):
        """Get a link to a GitHub issue."""

        github, _ = self.bot.get_github_app(interaction)
        await interaction.response.send_message(github.get_user().login)

    @app_commands.command()
    async def pr(self, interaction: Interaction):
        """Get a link to a GitHub pull request."""

        await interaction.response.defer(ephemeral=False)

    @app_commands.command()
    async def commit(self, interaction: Interaction):
        """Get a link to a GitHub commit."""

        await interaction.response.defer(ephemeral=False)

    @app_commands.command()
    async def login(self, interaction: Interaction):
        """Authorize GitHub Utils to make requests on behalf of your GitHub account."""

        user_id = interaction.user.id
        login_id = str(uuid.uuid4())

        with self.bot.db_session() as session:
            match session.get(UserLogin, user_id):
                case UserLogin() as login:
                    login.login_id = login_id
                case None:
                    login = UserLogin(user_id=user_id, login_id=login_id)

            session.add(login)
            session.commit()

        auth_url = self.env.github.get_login_url(state=login.model_dump_json())

        await interaction.response.send_message(
            view=View().add_item(Button(label="Login with GitHub", url=auth_url)),
            ephemeral=True,
        )

    @app_commands.command()
    async def logout(self, interaction: Interaction):
        """Remove your GitHub account from GitHub Utils."""

        with self.bot.db_session() as session:
            # TODO: this should delete the authorization too, but idk how
            # https://docs.github.com/en/rest/apps/oauth-applications?apiVersion=2022-11-28#delete-an-app-authorization
            if user_tokens := session.get(UserGitHubTokens, interaction.user.id):
                session.delete(user_tokens)
                session.commit()

                await interaction.response.send_message(
                    "✅ Successfully logged out.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "❌ Already logged out.",
                    ephemeral=True,
                )

    # /gh list

    gh_list = Group(
        name="list",
        description="Commands to list values from GitHub.",
    )

    @gh_list.command()
    async def issues(
        self,
        interaction: Interaction,
        repo: RepositoryParam,
    ):
        github, _ = self.bot.get_github_app(interaction)

        issues = github.get_repo(str(repo)).get_issues()

        await interaction.response.send_message(
            "\n".join(issue.title for issue in issues.get_page(0))
        )
