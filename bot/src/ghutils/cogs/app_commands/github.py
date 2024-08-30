from __future__ import annotations

import logging
import uuid

from discord import Interaction, app_commands
from discord.ext.commands import GroupCog
from discord.ui import Button, View

from ghutils.core.cog import GHUtilsCog
from ghutils.db.models import (
    UserGitHubTokens,
    UserLogin,
)
from ghutils.utils.discord.references import (
    CommitReference,
    IssueReference,
    PRReference,
)

logger = logging.getLogger(__name__)


class GitHubCog(GHUtilsCog, GroupCog, group_name="gh"):
    """GitHub-related commands."""

    # /gh

    @app_commands.command()
    async def issue(self, interaction: Interaction, issue: IssueReference):
        """Get a link to a GitHub issue."""

        await interaction.response.send_message(
            f"[#{issue.number}](<{issue.html_url}>): {issue.title}"
        )

    @app_commands.command()
    async def pr(self, interaction: Interaction, pr: PRReference):
        """Get a link to a GitHub pull request."""

        await interaction.response.send_message(
            f"[#{pr.number}](<{pr.html_url}>): {pr.title}"
        )

    @app_commands.command()
    async def commit(self, interaction: Interaction, commit: CommitReference):
        """Get a link to a GitHub commit."""

        await interaction.response.send_message(
            f"[{commit.sha[:12]}](<{commit.html_url}>): {commit.commit.message}"
        )

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

        auth_url = self.env.gh.get_login_url(state=login.model_dump_json())

        await interaction.response.send_message(
            view=View().add_item(Button(label="Login with GitHub", url=str(auth_url))),
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
