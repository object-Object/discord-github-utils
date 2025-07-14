from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Callable, List, Self, cast, overload

from discord import Color
from githubkit import Paginator, Response
from githubkit.rest import Issue, IssuePropPullRequest, PullRequest


class IssueState(Enum):
    OPEN = Color.from_rgb(63, 185, 80)
    CLOSED = Color.from_rgb(171, 125, 248)
    NOT_PLANNED = Color.from_rgb(145, 152, 161)

    def __init__(self, color: Color):
        self.color = color

    @classmethod
    def of(cls, issue: Issue) -> IssueState:
        match issue:
            case Issue(state="open"):
                return IssueState.OPEN
            case Issue(state="closed", state_reason="not_planned"):
                return IssueState.NOT_PLANNED
            case _:
                return IssueState.CLOSED


class PullRequestState(Enum):
    OPEN = Color.from_rgb(63, 185, 80)
    DRAFT = Color.from_rgb(145, 152, 161)
    MERGED = Color.from_rgb(171, 125, 248)
    CLOSED = Color.from_rgb(248, 81, 73)

    def __init__(self, color: Color):
        self.color = color

    @overload
    @classmethod
    def of(cls, pr: Issue) -> PullRequestState | None: ...

    @overload
    @classmethod
    def of(cls, pr: PullRequest) -> PullRequestState: ...

    @classmethod
    def of(cls, pr: Issue | PullRequest) -> PullRequestState | None:
        match pr:
            case Issue() if not pr.pull_request:
                return None

            case (
                Issue(state="open", draft=True) | PullRequest(state="open", draft=True)
            ):
                return PullRequestState.DRAFT

            case Issue(state="open") | PullRequest(state="open"):
                return PullRequestState.OPEN

            case (
                Issue(
                    state="closed",
                    pull_request=IssuePropPullRequest(merged_at=datetime()),
                )
                | PullRequest(state="closed", merged=True)
            ):
                return PullRequestState.MERGED

            case _:
                return PullRequestState.CLOSED


class CommitCheckState(Enum):
    SUCCESS = Color.from_rgb(35, 134, 54)
    FAILURE = Color.from_rgb(218, 54, 51)
    PENDING = Color.from_rgb(158, 106, 3)
    NEUTRAL = None

    def __init__(self, color: Color | None):
        self.color = color


@dataclass
class RepositoryName:
    owner: str
    repo: str

    @classmethod
    def parse(cls, value: str) -> Self:
        if "/" not in value:
            raise ValueError("Missing '/' between username and repository")

        owner, repo = value.split("/", maxsplit=1)
        if not (owner and repo):
            raise ValueError("Owner and/or repository is blank")

        return cls(owner=owner, repo=repo)

    @classmethod
    def try_parse(cls, value: str) -> Self | None:
        try:
            return cls.parse(value)
        except ValueError:
            return None

    def __str__(self) -> str:
        return f"{self.owner}/{self.repo}"


class SmartPaginator[RT](Paginator[RT]):
    """Subclass of `Paginator` that allows checking the `total_count` field (or similar)
    provided in some requests, to avoid making an unnecessary extra request after the
    final page.

    Only supports async, since this bot only uses async requests.
    """

    def __init__[**CP, CT](
        self,
        request: Callable[CP, Awaitable[Response[CT]]],
        map_func: Callable[[Response[CT]], list[RT]],
        limit_func: Callable[[Response[CT]], int],
        page: int = 1,
        per_page: int = 100,
        *args: CP.args,
        **kwargs: CP.kwargs,
    ):
        super().__init__(
            request=request,
            map_func=map_func,
            page=page,
            per_page=per_page,
            *args,
            **kwargs,
        )

        self.request = request
        self.map_func = map_func
        self.limit_func = limit_func

        self._limit: int | None = None
        self._prev_pages_data_count = 0

    async def _aget_next_page(self) -> List[RT]:
        if (
            self._limit is not None
            and self._prev_pages_data_count + self._index >= self._limit
        ):
            return []

        self._prev_pages_data_count += len(self._cached_data)
        response = cast(
            Response[Any],
            await self.request(
                *self.args,
                **self.kwargs,
                page=self._current_page,  # type: ignore
                per_page=self._per_page,  # type: ignore
            ),
        )
        self._cached_data = self.map_func(response)
        self._limit = self.limit_func(response)
        self._index = 0
        self._current_page += 1
        return self._cached_data


async def gh_request[T](future: Awaitable[Response[T]]) -> T:
    """Helper function to simplify extracting the parsed data from GitHub requests."""
    resp = await future
    return resp.parsed_data


def shorten_sha(sha: str):
    return sha[:10]


def issue_or_pr_state(issue: Issue | PullRequest) -> IssueState | PullRequestState:
    if isinstance(issue, PullRequest):
        return PullRequestState.of(issue)
    return PullRequestState.of(issue) or IssueState.of(issue)
