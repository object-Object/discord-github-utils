from __future__ import annotations

import logging
import uuid

from discord import Color, Embed, Interaction, app_commands
from discord.ext.commands import GroupCog
from discord.ui import Button, View
from githubkit.rest import Issue

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
from ghutils.utils.strings import truncate_str

logger = logging.getLogger(__name__)


class GitHubCog(GHUtilsCog, GroupCog, group_name="gh"):
    """GitHub-related commands."""

    # /gh

    @app_commands.command()
    @app_commands.rename(reference="issue")
    async def issue(
        self,
        interaction: Interaction,
        reference: IssueReference,
        ephemeral: bool = True,
    ):
        """Get a link to a GitHub issue."""

        repo, issue = reference

        if issue.body:
            description = truncate_str(issue.body, limit=200, message="...")
        else:
            description = None

        match issue:
            case Issue(state="closed", state_reason="not_planned"):
                color = "rgb(145, 152, 161)"
            case Issue(state="closed"):
                color = "rgb(171, 125, 248)"
            case _:  # open
                color = "rgb(63, 185, 80)"

        embed = (
            Embed(
                title=f"#{issue.number}: {issue.title}",
                url=issue.html_url,
                description=description,
                color=Color.from_str(color),
            )
            .set_footer(
                text=f"{repo}#{issue.number}",
            )
            .add_field(
                name="Opened",
                value=f"<t:{int(issue.created_at.timestamp())}:f>",
            )
        )

        if issue.closed_at:
            embed.add_field(
                name="Closed",
                value=f"<t:{int(issue.closed_at.timestamp())}:f>",
            )

        if user := issue.user:
            embed.set_author(
                name=user.login,
                url=user.html_url,
                icon_url=user.avatar_url,
            )

        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @app_commands.command()
    @app_commands.rename(reference="pr")
    async def pr(
        self,
        interaction: Interaction,
        reference: PRReference,
        ephemeral: bool = True,
    ):
        """Get a link to a GitHub pull request."""

        repo, pr = reference

        await interaction.response.send_message(
            f"[#{pr.number}](<{pr.html_url}>): {pr.title}"
        )

    @app_commands.command()
    @app_commands.rename(reference="commit")
    async def commit(
        self,
        interaction: Interaction,
        reference: CommitReference,
        ephemeral: bool = True,
    ):
        """Get a link to a GitHub commit."""

        repo, commit = reference

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
