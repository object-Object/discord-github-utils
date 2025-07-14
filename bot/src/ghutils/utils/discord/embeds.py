from __future__ import annotations

from discord import Embed
from githubkit.rest import Issue, IssuePropPullRequest, PullRequest, SimpleUser

from ..github import (
    IssueState,
    PullRequestState,
    RepositoryName,
)
from ..strings import truncate_str


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
