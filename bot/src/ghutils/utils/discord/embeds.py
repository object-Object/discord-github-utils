from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from discord import Embed, Interaction, Message
from githubkit import GitHub
from githubkit.exception import GitHubException
from githubkit.rest import Commit, Issue, IssuePropPullRequest, PullRequest, SimpleUser

from ghutils.utils.discord.visibility import MessageContents

from ..github import (
    CommitCheckState,
    IssueState,
    PullRequestState,
    RepositoryName,
    SmartPaginator,
    gh_request,
    shorten_sha,
)
from ..strings import truncate_str
from .references import IssueReference, IssueReferenceTransformer

logger = logging.getLogger(__name__)


def set_embed_author(embed: Embed, user: SimpleUser):
    embed.set_author(
        name=user.login,
        url=user.html_url,
        icon_url=user.avatar_url,
    )
    return embed


def create_issue_embed(
    repo: RepositoryName,
    issue: Issue | PullRequest,
    *,
    add_body: bool = True,
):
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

    if issue.body and add_body:
        embed.description = truncate_str(issue.body, 200)

    if issue.user:
        set_embed_author(embed, issue.user)

    return embed


_ISSUE_PATTERN = re.compile(
    r"""
    (?<![a-zA-Z`</])
    (?P<value>
        (?P<repo>[\w-]+/[\w-]+)?
        \#
        (?P<reference>[0-9]+)
    )
    (?![a-zA-Z`>])
    """,
    flags=re.VERBOSE,
)


async def create_issue_embeds(
    github: GitHub[Any],
    interaction: Interaction,
    message: Message,
):
    seen = set[str]()
    issues = list[IssueReference]()
    transformer = IssueReferenceTransformer()

    for match in _ISSUE_PATTERN.finditer(message.content):
        value = match.group("value")
        try:
            repo, issue = await transformer.transform_with_github(
                github, interaction, value
            )
        except Exception:
            logger.warning(
                f"Failed to transform issue reference: {value}", exc_info=True
            )
            continue

        if issue.html_url in seen:
            continue

        seen.add(issue.html_url)
        issues.append((repo, issue))

    content = None
    embeds = list[Embed]()
    match issues:
        case []:
            content = "❌ No issue references found."
        case [reference]:
            embeds.append(create_issue_embed(*reference))
        case _:
            embeds.extend(
                create_issue_embed(*reference, add_body=False) for reference in issues
            )
    return MessageContents(
        command=interaction.command,
        content=content,
        embeds=embeds,
    )


async def create_commit_embed(
    github: GitHub[Any],
    repo: RepositoryName,
    commit: Commit,
):
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
