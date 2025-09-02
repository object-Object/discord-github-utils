from __future__ import annotations

import logging
import re
from typing import Any

from discord import Embed, Interaction, Message
from githubkit import GitHub
from githubkit.rest import Issue, IssuePropPullRequest, PullRequest

from ghutils.ui.components.visibility import MessageContents
from ghutils.utils.discord.embeds import set_embed_author, truncate_markdown_description
from ghutils.utils.discord.references import IssueReference, IssueReferenceTransformer
from ghutils.utils.github import IssueState, PullRequestState, RepositoryName
from ghutils.utils.strings import truncate_str

logger = logging.getLogger(__name__)


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
        embed.description = truncate_markdown_description(issue.body)

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
