from __future__ import annotations

import logging
import textwrap
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import pfzy
from discord import Color, Embed, Interaction, app_commands
from discord.app_commands import Range
from discord.ext.commands import GroupCog
from discord.ui import Button, View
from githubkit import GitHub
from githubkit.exception import GitHubException, RequestFailed
from githubkit.rest import Issue, IssuePropPullRequest, PullRequest, SimpleUser
from more_itertools import consecutive_groups, ilen
from yarl import URL

from ghutils.common.__version__ import VERSION
from ghutils.core.cog import GHUtilsCog, SubGroup
from ghutils.core.types import InvalidInputError, LoginState, NotLoggedInError
from ghutils.db.models import (
    UserGitHubTokens,
    UserLogin,
)
from ghutils.utils.discord.embeds import set_embed_author
from ghutils.utils.discord.references import (
    CommitReference,
    IssueReference,
    PRReference,
)
from ghutils.utils.discord.transformers import FullRepositoryOption
from ghutils.utils.discord.visibility import MessageVisibility, respond_with_visibility
from ghutils.utils.github import (
    CommitCheckState,
    IssueState,
    PullRequestState,
    RepositoryName,
    SmartPaginator,
    gh_request,
    shorten_sha,
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
        visibility: MessageVisibility = "private",
    ):
        """Get a link to a GitHub issue."""

        await respond_with_visibility(
            interaction,
            visibility,
            embed=_create_issue_embed(*reference),
        )

    @app_commands.command()
    @app_commands.rename(reference="pr")
    async def pr(
        self,
        interaction: Interaction,
        reference: PRReference,
        visibility: MessageVisibility = "private",
    ):
        """Get a link to a GitHub pull request."""

        await respond_with_visibility(
            interaction,
            visibility,
            embed=_create_issue_embed(*reference),
        )

    @app_commands.command()
    @app_commands.rename(reference="commit")
    async def commit(
        self,
        interaction: Interaction,
        reference: CommitReference,
        visibility: MessageVisibility = "private",
    ):
        """Get a link to a GitHub commit."""

        repo, commit = reference

        async with self.bot.github_app(interaction) as (github, _):
            state = await _get_commit_check_state(github, repo, commit.sha)

        short_sha = shorten_sha(commit.sha)

        message = commit.commit.message
        description = None
        if "\n" in message:
            message, description = message.split("\n", maxsplit=1)
            description = truncate_str(description.strip(), 200)

        embed = Embed(
            title=truncate_str(f"[{short_sha}] {message}", 256),
            description=description,
            url=commit.html_url,
            color=state.color,
        ).set_footer(
            text=f"{repo}@{short_sha}",
        )

        if (author := commit.commit.author) and author.date:
            try:
                embed.timestamp = datetime.fromisoformat(author.date)
            except ValueError:
                pass

        if isinstance(commit.author, SimpleUser):
            set_embed_author(embed, commit.author)

        await respond_with_visibility(interaction, visibility, embed=embed)

    @app_commands.command()
    async def repo(
        self,
        interaction: Interaction,
        repo: FullRepositoryOption,
        visibility: MessageVisibility = "private",
    ):
        """Get a link to a GitHub repository."""

        async with self.bot.github_app(interaction) as (github, _):
            result = await github.async_graphql(
                """
                query($owner: String!, $name: String!) {
                    repository(owner: $owner, name: $name) {
                        openGraphImageUrl
                    }
                }
                """,
                {
                    "owner": repo.owner.login,
                    "name": repo.name,
                },
            )
            image_url: str = result["repository"]["openGraphImageUrl"]

        embed = Embed(
            title=repo.full_name,
            description=repo.description,
            url=repo.html_url,
        ).set_image(
            url=image_url,
        )
        set_embed_author(embed, repo.owner)

        await respond_with_visibility(interaction, visibility, embed=embed)

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

    @app_commands.command()
    async def status(
        self,
        interaction: Interaction,
        visibility: MessageVisibility = "private",
    ):
        """Show information about GitHub Utils."""

        if info := self.env.deployment:
            color = Color.green()
            commit_url = f"https://github.com/object-Object/discord-github-utils/commit/{info.commit_sha}"
            commit_info = textwrap.dedent(
                f"""\
                    [{info.short_commit_sha}]({commit_url}): {info.commit_message}
                    {_discord_date(info.commit_timestamp)}"""
            )
            deployment_time_info = _discord_date(info.timestamp)
        else:
            color = Color.orange()
            commit_info = "Unknown"
            deployment_time_info = "Unknown"

        embed = (
            Embed(
                title="Bot Status",
                color=color,
            )
            .set_footer(text=f"v{VERSION}")
            .add_field(
                name="Deployed commit",
                value=commit_info,
                inline=False,
            )
            .add_field(
                name="Deployment time",
                value=deployment_time_info,
                inline=False,
            )
            .add_field(
                name="Uptime",
                value=_discord_date(self.bot.start_time),
                inline=False,
            )
            .add_field(
                name="Servers",
                value=f"{len(self.bot.guilds)}",
            )
            .add_field(
                name="Cogs",
                value=f"{len(self.bot.cogs)}",
            )
            .add_field(
                name="Commands",
                value=f"{ilen(self.bot.tree.walk_commands())}",
            )
        )

        await respond_with_visibility(interaction, visibility, embed=embed)

    class Search(SubGroup):
        """Search for things on GitHub."""

        @app_commands.command()
        async def files(
            self,
            interaction: Interaction,
            repo: FullRepositoryOption,
            query: Range[str, 1, 128],
            ref: Range[str, 1, 255] | None = None,
            exact: bool = False,
            limit: Range[int, 1, 25] = 5,
            visibility: MessageVisibility = "private",
        ):
            """Search for files in a repository by name.

            Args:
                ref: Branch name, tag name, or commit to search in. Defaults to the
                    default branch of the repo.
                exact: If true, use exact search; otherwise use fuzzy search.
                limit: Maximum number of results to show.
            """

            async with self.bot.github_app(interaction) as (github, state):
                if state != LoginState.LOGGED_IN:
                    raise NotLoggedInError()

                if ref is None:
                    ref = repo.default_branch

                try:
                    tree = await gh_request(
                        github.rest.git.async_get_tree(
                            repo.owner.login,
                            repo.name,
                            ref,
                            recursive="1",
                        )
                    )
                except RequestFailed as e:
                    if e.response.status_code == 404:  # pyright: ignore[reportUnknownMemberType]
                        raise InvalidInputError(
                            value=ref,
                            message=f"Ref does not exist in `{repo.full_name}`.",
                        )
                    raise

                sha = tree.sha[:12]
                tree_dict = {item.path: item for item in tree.tree if item.path}

                matches = await pfzy.fuzzy_match(
                    query,
                    list(tree_dict.keys()),
                    scorer=pfzy.substr_scorer if exact else pfzy.fzy_scorer,
                )

                embed = (
                    Embed(
                        title="File search results",
                    )
                    .set_author(
                        name=repo.full_name,
                        url=repo.html_url,
                        icon_url=repo.owner.avatar_url,
                    )
                    .set_footer(
                        text=f"{repo.full_name}@{ref}  •  Total results: {len(matches)}",
                    )
                )

                # code search only works on the default branch
                # so don't add the link otherwise, since it won't be useful
                if ref == repo.default_branch:
                    embed.url = str(
                        URL("https://github.com/search").with_query(
                            type="code",
                            q=f'repo:{repo.full_name} path:"{query}"',
                        )
                    )

                if matches:
                    embed.color = Color.green()
                else:
                    embed.description = "⚠️ No matches found."
                    embed.color = Color.red()

                size = 0
                for match in matches[:limit]:
                    path: str = match["value"]
                    indices: list[int] = match["indices"]

                    item = tree_dict[path]

                    icon = "📁" if item.type == "tree" else "📄"
                    url = f"https://github.com/{repo.full_name}/{item.type}/{sha}/{item.path}"

                    parts = list[str]()
                    index = 0
                    for group in consecutive_groups(indices):
                        group = list(group)
                        parts += [
                            # everything before the start of the group
                            path[index : group[0]],
                            "**",
                            # everything in the group
                            path[group[0] : group[-1] + 1],
                            "**",
                        ]
                        index = group[-1] + 1
                    # everything after the last group
                    parts.append(path[index:])
                    highlighted_path = "".join(parts)

                    name = f"{icon} {Path(path).name}"
                    value = f"[{highlighted_path}]({url})"

                    size += len(name) + len(value)
                    if size > 5000:
                        break

                    embed.add_field(name=name, value=value, inline=False)

                await respond_with_visibility(interaction, visibility, embed=embed)


def _discord_date(timestamp: int | float | datetime):
    match timestamp:
        case int():
            pass
        case float():
            timestamp = int(timestamp)
        case datetime():
            timestamp = int(timestamp.timestamp())
    return f"<t:{timestamp}:f> (<t:{timestamp}:R>)"


def _create_issue_embed(repo: RepositoryName, issue: Issue | PullRequest):
    match issue:
        case Issue(pull_request=IssuePropPullRequest()) | PullRequest():
            issue_type = "PR"
            state = PullRequestState.of(issue)
            assert state
        case Issue():
            issue_type = "Issue"
            state = IssueState.of(issue)

    embed = Embed(
        title=truncate_str(f"[{issue_type} #{issue.number}] {issue.title}", 256),
        url=issue.html_url,
        timestamp=issue.created_at,
        color=state.color,
    ).set_footer(
        text=f"{repo}#{issue.number}",
    )

    if issue.body:
        embed.description = truncate_str(issue.body, 200)

    if issue.user:
        set_embed_author(embed, issue.user)

    return embed


# we need to look at both checks and commit statuses
# https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/about-status-checks#types-of-status-checks-on-github
# if anything is in progress, return PENDING
# else if anything failed, return FAILURE
# else if anything succeeded, return SUCCESS
# else return PENDING
async def _get_commit_check_state(
    github: GitHub[Any],
    repo: RepositoryName,
    sha: str,
) -> CommitCheckState:
    state = CommitCheckState.NEUTRAL

    # checks
    try:
        async for suite in SmartPaginator(
            github.rest.checks.async_list_suites_for_ref,
            owner=repo.owner,
            repo=repo.repo,
            ref=sha,
            map_func=lambda resp: resp.parsed_data.check_suites,
            limit_func=lambda resp: resp.parsed_data.total_count,
        ):
            match suite.status:
                case "queued":
                    # this is the default status
                    # it seems to show up for suites that aren't actually in the UI
                    # so just ignore it
                    pass
                case "completed":
                    match suite.conclusion:
                        case "success":
                            if state is not CommitCheckState.FAILURE:
                                state = CommitCheckState.SUCCESS
                        case "failure" | "timed_out" | "startup_failure":
                            state = CommitCheckState.FAILURE
                        case _:
                            pass
                case _:
                    return CommitCheckState.PENDING
    except GitHubException:
        pass

    if state is CommitCheckState.FAILURE:
        return state

    # commit statuses
    # if we get to this point, either all checks passed or there are no checks
    try:
        combined_status = await gh_request(
            github.rest.repos.async_get_combined_status_for_ref(
                owner=repo.owner,
                repo=repo.repo,
                ref=sha,
            )
        )
        match combined_status.state:
            case "success":
                return CommitCheckState.SUCCESS
            case "failure":
                return CommitCheckState.FAILURE
            case _:
                pass
    except GitHubException:
        pass

    return state
