from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from functools import cached_property
from typing import Awaitable

from discord import Color
from githubkit import Response
from githubkit.rest import Issue, PullRequest


class IssueState(Enum):
    OPEN = auto()
    CLOSED = auto()
    NOT_PLANNED = auto()

    @classmethod
    def of(cls, issue: Issue) -> IssueState:
        match issue:
            case Issue(state="open"):
                return IssueState.OPEN
            case Issue(state="closed", state_reason="not_planned"):
                return IssueState.NOT_PLANNED
            case _:
                return IssueState.CLOSED

    @cached_property
    def color(self):
        match self:
            case IssueState.OPEN:
                return Color.from_rgb(63, 185, 80)
            case IssueState.CLOSED:
                return Color.from_rgb(171, 125, 248)
            case IssueState.NOT_PLANNED:
                return Color.from_rgb(145, 152, 161)


class PullRequestState(Enum):
    OPEN = auto()
    DRAFT = auto()
    MERGED = auto()
    CLOSED = auto()

    @classmethod
    def of(cls, pr: PullRequest) -> PullRequestState:
        match pr:
            case PullRequest(state="open", draft=True):
                return PullRequestState.DRAFT
            case PullRequest(state="open"):
                return PullRequestState.OPEN
            case PullRequest(state="closed", merged=True):
                return PullRequestState.MERGED
            case _:
                return PullRequestState.CLOSED

    @cached_property
    def color(self):
        match self:
            case PullRequestState.OPEN:
                return Color.from_rgb(63, 185, 80)
            case PullRequestState.DRAFT:
                return Color.from_rgb(145, 152, 161)
            case PullRequestState.MERGED:
                return Color.from_rgb(171, 125, 248)
            case PullRequestState.CLOSED:
                return Color.from_rgb(248, 81, 73)


class CommitStatusState(Enum):
    SUCCESS = auto()
    FAILURE = auto()
    PENDING = auto()

    @cached_property
    def color(self):
        match self:
            case CommitStatusState.SUCCESS:
                return Color.from_rgb(35, 134, 54)
            case CommitStatusState.FAILURE:
                return Color.from_rgb(218, 54, 51)
            case CommitStatusState.PENDING:
                return None


@dataclass
class Repository:
    owner: str
    repo: str

    @classmethod
    def parse(cls, value: str):
        if "/" in value:
            owner, repo = value.split("/")
            if owner and repo:
                return cls(owner=owner, repo=repo)

    def __str__(self) -> str:
        return f"{self.owner}/{self.repo}"


async def gh_request[T](future: Awaitable[Response[T]]) -> T:
    """Helper function to simplify extracting the parsed data from GitHub requests."""
    resp = await future
    return resp.parsed_data


def short_sha(sha: str):
    return sha[:10]
