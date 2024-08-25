from __future__ import annotations

import logging
import uuid
from typing import Any

from discord import Interaction, app_commands
from discord.ext.commands import GroupCog
from discord.ui import Button, View
from githubkit import GitHub

from ghutils.core.cog import GHUtilsCog, SubGroup
from ghutils.db.models import (
    UserGitHubTokens,
    UserLogin,
)
from ghutils.utils.discord.references import (
    CommitReference,
    IssueReference,
    PRReference,
)
from ghutils.utils.discord.transformers import RepositoryParam
from ghutils.utils.github import Repository

logger = logging.getLogger(__name__)


@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
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

    class List(SubGroup):
        """List values from GitHub."""

        @app_commands.command()
        async def issues(
            self,
            interaction: Interaction,
            repo: RepositoryParam,
        ):
            async with self.bot.github_app(interaction) as (github, _):
                issues = [issue async for issue in _list_issues(github, repo, limit=10)]

                await interaction.response.send_message(
                    "\n".join(f"- {issue.title}" for issue in issues)
                )


async def _list_issues(
    github: GitHub[Any],
    repo: Repository,
    *,
    limit: int | None = None,
):
    n = 0
    async for issue in github.paginate(
        github.rest.issues.async_list_for_repo,
        owner=repo.owner,
        repo=repo.repo,
        state="open",
    ):
        if issue.pull_request:
            continue
        yield issue
        n += 1
        if limit and n >= limit:
            break
