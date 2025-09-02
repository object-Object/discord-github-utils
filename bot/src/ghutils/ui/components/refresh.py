from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from re import Match
from typing import Any, override

from discord import Color, Embed, Interaction, Message
from discord.ui import Button, DynamicItem, Item
from githubkit import GitHub
from githubkit.rest import Commit, Issue
from pydantic import TypeAdapter
from pydantic.dataclasses import dataclass as pydantic_dataclass

from ghutils.core.bot import GHUtilsBot
from ghutils.core.types import LoginState
from ghutils.ui.embeds.commits import create_commit_embed
from ghutils.ui.embeds.issues import (
    create_issue_embed,
    create_issue_embeds,
)
from ghutils.utils.discord.mentions import relative_timestamp
from ghutils.utils.discord.references import (
    CommitReference,
    IssueReference,
    PRReference,
)
from ghutils.utils.github import RepositoryName, gh_request


@pydantic_dataclass
class RefreshIssueButton(
    DynamicItem[Button[Any]],
    template=r"RefreshIssue:(?P<repo_id>[0-9]+):(?P<issue>[0-9]+)",
):
    repo_id: int
    issue: int

    def __post_init__(self):
        super().__init__(
            Button(
                emoji="🔄",
                custom_id=f"RefreshIssue:{self.repo_id}:{self.issue}",
            )
        )

    @classmethod
    @override
    async def from_custom_id(
        cls,
        interaction: Interaction,
        item: Item[Any],
        match: Match[str],
    ):
        return TypeAdapter(cls).validate_python(match.groupdict())

    @classmethod
    async def from_reference(
        cls,
        github: GitHub[Any],
        reference: IssueReference | PRReference,
    ):
        repo_name, issue = reference
        repo = await gh_request(
            github.rest.repos.async_get(owner=repo_name.owner, repo=repo_name.repo)
        )
        return cls(
            repo_id=repo.id,
            issue=issue.number,
        )

    @override
    async def callback(self, interaction: Interaction):
        async with GHUtilsBot.github_app_of(interaction) as (github, state):
            if not await _check_ratelimit(interaction, state):
                return

            # NOTE: this is an undocumented endpoint, but it seems like it's probably stable (https://stackoverflow.com/a/75527854)
            # we use this because user and repository names may be too long to fit in a custom id
            issue = await gh_request(
                github.arequest(  # pyright: ignore[reportUnknownMemberType]
                    "GET",
                    f"/repositories/{self.repo_id}/issues/{self.issue}",
                    response_model=Issue,
                )
            )

            repo = RepositoryName.from_url(issue.html_url)

            await interaction.response.edit_message(
                embed=create_issue_embed(repo, issue),
            )


@dataclass
class RefreshIssuesButton(
    DynamicItem[Button[Any]],
    template=r"RefreshIssues:(?P<message_id>[0-9]+)",
):
    message: Message

    def __post_init__(self):
        super().__init__(
            Button(
                emoji="🔄",
                custom_id=f"RefreshIssues:{self.message.id}",
            )
        )

    @classmethod
    @override
    async def from_custom_id(
        cls,
        interaction: Interaction,
        item: Item[Any],
        match: Match[str],
    ):
        assert interaction.message is not None
        message_id = int(match["message_id"])
        return cls(
            message=await interaction.message.channel.fetch_message(message_id),
        )

    @override
    async def callback(self, interaction: Interaction):
        async with GHUtilsBot.github_app_of(interaction) as (github, state):
            if not await _check_ratelimit(interaction, state):
                return

            # disable the button while we're working to give a loading indication
            self.item.disabled = True
            await interaction.response.edit_message(view=self.view)

            self.item.disabled = False
            try:
                contents = await create_issue_embeds(github, interaction, self.message)
                await contents.edit_original_response(interaction, view=self.view)
            except Exception:
                await interaction.edit_original_response(view=self.view)
                raise


@pydantic_dataclass
class RefreshCommitButton(
    DynamicItem[Button[Any]],
    template=r"RefreshCommit:(?P<repo_id>[0-9]+):(?P<sha>[^:]+)",
):
    repo_id: int
    sha: str

    def __post_init__(self):
        super().__init__(
            Button(
                emoji="🔄",
                custom_id=f"RefreshCommit:{self.repo_id}:{self.sha}",
            )
        )

    @classmethod
    @override
    async def from_custom_id(
        cls,
        interaction: Interaction,
        item: Item[Any],
        match: Match[str],
    ):
        return TypeAdapter(cls).validate_python(match.groupdict())

    @classmethod
    async def from_reference(
        cls,
        github: GitHub[Any],
        reference: CommitReference,
    ):
        repo_name, commit = reference
        repo = await gh_request(
            github.rest.repos.async_get(owner=repo_name.owner, repo=repo_name.repo)
        )
        return cls(
            repo_id=repo.id,
            sha=commit.sha,
        )

    @override
    async def callback(self, interaction: Interaction):
        async with GHUtilsBot.github_app_of(interaction) as (github, state):
            if not await _check_ratelimit(interaction, state):
                return

            commit = await gh_request(
                github.arequest(  # pyright: ignore[reportUnknownMemberType]
                    "GET",
                    f"/repositories/{self.repo_id}/commits/{self.sha}",
                    response_model=Commit,
                )
            )

            repo = RepositoryName.from_url(commit.html_url)

            await interaction.response.edit_message(
                embed=await create_commit_embed(github, repo, commit),
            )


async def _check_ratelimit(interaction: Interaction, state: LoginState) -> bool:
    now = datetime.now(UTC)
    if (
        state.logged_out()
        and interaction.message
        and (edited_at := interaction.message.edited_at)
        and (retry_time := edited_at + timedelta(seconds=60))
        and retry_time > now
    ):
        await interaction.response.send_message(
            embed=Embed(
                title="Slow down!",
                description="This button can only be used once per minute by unauthenticated users."
                + f" Use `/gh login` to authenticate, or try again {relative_timestamp(retry_time)}.",
                color=Color.red(),
            ),
            ephemeral=True,
            # delete the message after the timeout, but wait at least 10 seconds to allow reading it fully
            delete_after=max((retry_time - now).total_seconds(), 10),
        )
        return False
    return True
