from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Iterable, Literal

from discord import Interaction
from discord.app_commands import Choice, Transform, Transformer
from githubkit import GitHub, Response
from githubkit.exception import GitHubException, RequestFailed
from githubkit.rest import Commit, Issue, PullRequest

from ghutils.core.bot import GHUtilsBot
from ghutils.core.types import LoginState
from ghutils.db.config import get_configs

from ..github import RepositoryName, gh_request, shorten_sha
from ..strings import truncate_str

logger = logging.getLogger(__name__)

URL_PATTERN = re.compile(
    r"(?:https?://)?github.com/(?P<repo>[\w-]+/[\w-]+)/(?P<path>[\w-]+)/(?P<reference>[\w-]+)"
)


class ReferenceTransformer[T](Transformer, ABC):
    @property
    @abstractmethod
    def separator(self) -> str: ...

    @property
    @abstractmethod
    def url_path(self) -> str: ...

    @property
    @abstractmethod
    def reference_pattern(self) -> str: ...

    @abstractmethod
    async def resolve_reference(
        self,
        github: GitHub[Any],
        repo: RepositoryName,
        reference: str,
    ) -> T: ...

    @abstractmethod
    async def search_for_autocomplete(
        self,
        github: GitHub[Any],
        repo: RepositoryName,
        search: str,
    ) -> Iterable[tuple[str | int, str]]:
        """Returns a list of `(reference, description)`.

        For example, issues would return a list of `(issue_number, issue_title)`.
        """

    async def transform(
        self,
        interaction: Interaction,
        value: str,
    ) -> tuple[RepositoryName, T]:
        repo, raw_reference = await self.get_repo_and_reference(interaction, value)

        match = re.match(rf"^({self.reference_pattern})", raw_reference)
        if not match:
            raise ValueError(f"Malformed reference: {raw_reference}")

        async with GHUtilsBot.github_app_of(interaction) as (github, _):
            try:
                return repo, await self.resolve_reference(github, repo, match[1])
            except GitHubException as e:
                match e:
                    case RequestFailed(response=Response(status_code=404)):
                        raise ValueError(
                            f"Failed to resolve reference '{value}': Not found"
                        )
                    case _:
                        logger.warning(e)
                        raise ValueError(f"Failed to resolve reference '{value}': {e}")

    async def autocomplete(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        interaction: Interaction,
        value: str,
    ) -> list[Choice[str]]:
        async with GHUtilsBot.github_app_of(interaction) as (github, state):
            if state != LoginState.LOGGED_IN:
                return []

            try:
                repo, search = await self.get_repo_and_reference(interaction, value)
            except ValueError:
                return []

            try:
                return [
                    self.build_choice(repo, reference, description)
                    for reference, description in await self.search_for_autocomplete(
                        github, repo, search
                    )
                ]
            except RequestFailed:
                return []
            except GitHubException as e:
                logger.warning(e)
                return []

    async def get_repo_and_reference(
        self,
        interaction: Interaction,
        value: str,
    ) -> tuple[RepositoryName, str]:
        if (match := URL_PATTERN.match(value)) and match["path"] == self.url_path:
            raw_repo = match["repo"]
            rest = match["reference"]
        elif self.separator in value:
            raw_repo, rest = value.split(self.separator, maxsplit=1)
        else:
            raw_repo = ""
            rest = value
        rest = rest.strip()

        if not raw_repo:
            with GHUtilsBot.db_session_of(interaction) as session:
                configs = get_configs(session, interaction)
                if repo := configs.default_repo:
                    return repo, rest
            raise ValueError(f"Missing username and repository: {value}")

        repo = RepositoryName.parse(raw_repo)

        return repo, rest

    def build_choice(
        self,
        repo: RepositoryName,
        reference: str | int,
        description: str,
    ) -> Choice[str]:
        value = f"{repo}{self.separator}{reference}"
        name = truncate_str(f"{value}: {description}", 100)
        return Choice(name=name, value=value)


class IssueOrPRReferenceTransformer[T](ReferenceTransformer[T]):
    @property
    @abstractmethod
    def issue_type(self) -> Literal["issue", "pr"]: ...

    @property
    def separator(self):
        return "#"

    @property
    def reference_pattern(self):
        return r"\d+"

    async def search_for_autocomplete(
        self,
        github: GitHub[Any],
        repo: RepositoryName,
        search: str,
    ) -> list[tuple[str | int, str]]:
        results = await gh_request(
            github.rest.search.async_issues_and_pull_requests(
                f"{search} is:{self.issue_type} repo:{repo}",
                per_page=25,
            )
        )
        return [(result.number, result.title) for result in results.items]


class IssueReferenceTransformer(IssueOrPRReferenceTransformer[Issue]):
    @property
    def url_path(self):
        return "issues"

    @property
    def issue_type(self):
        return "issue"

    async def resolve_reference(
        self,
        github: GitHub[Any],
        repo: RepositoryName,
        reference: str,
    ) -> Issue:
        return await gh_request(
            github.rest.issues.async_get(
                owner=repo.owner,
                repo=repo.repo,
                issue_number=int(reference),
            )
        )


class PRReferenceTransformer(IssueOrPRReferenceTransformer[PullRequest]):
    @property
    def url_path(self):
        return "pull"

    @property
    def issue_type(self):
        return "pr"

    async def resolve_reference(
        self,
        github: GitHub[Any],
        repo: RepositoryName,
        reference: str,
    ) -> PullRequest:
        return await gh_request(
            github.rest.pulls.async_get(
                owner=repo.owner,
                repo=repo.repo,
                pull_number=int(reference),
            )
        )


class CommitReferenceTransformer(ReferenceTransformer[Commit]):
    @property
    def separator(self):
        return "@"

    @property
    def url_path(self):
        return "commit"

    @property
    def reference_pattern(self):
        return r"[0-9a-f]{5,40}"

    async def resolve_reference(
        self,
        github: GitHub[Any],
        repo: RepositoryName,
        reference: str,
    ) -> Commit:
        return await gh_request(
            github.rest.repos.async_get_commit(
                owner=repo.owner,
                repo=repo.repo,
                ref=reference,
            )
        )

    async def search_for_autocomplete(
        self,
        github: GitHub[Any],
        repo: RepositoryName,
        search: str,
    ) -> list[tuple[str | int, str]]:
        if search:
            resp = await github.rest.search.async_commits(
                f"{search} repo:{repo}",
                per_page=25,
            )
            results = resp.parsed_data.items
        else:
            # commit search doesn't allow an empty search, so list recent commits instead
            results = await gh_request(
                github.rest.repos.async_list_commits(
                    repo.owner,
                    repo.repo,
                    per_page=25,
                )
            )

        return [
            (shorten_sha(result.sha), result.commit.message.split("\n")[0])
            for result in results
        ]


IssueReference = Transform[tuple[RepositoryName, Issue], IssueReferenceTransformer]

PRReference = Transform[tuple[RepositoryName, PullRequest], PRReferenceTransformer]

CommitReference = Transform[tuple[RepositoryName, Commit], CommitReferenceTransformer]
