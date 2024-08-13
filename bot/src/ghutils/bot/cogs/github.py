from __future__ import annotations

import logging
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Iterable, Literal

from discord import Interaction, app_commands
from discord.app_commands import Choice, Group, Transform, Transformer
from discord.ext.commands import GroupCog
from discord.ui import Button, View
from githubkit import GitHub
from githubkit.exception import GitHubException, RequestFailed
from githubkit.rest import Issue, PullRequest

from ghutils.bot.core import GHUtilsCog
from ghutils.bot.core.bot import GHUtilsBot
from ghutils.bot.core.types import LoginState
from ghutils.bot.db.models import UserGitHubTokens, UserLogin
from ghutils.bot.utils.github import gh_request
from ghutils.bot.utils.strings import truncate_str

logger = logging.getLogger(__name__)


@dataclass
class Repository:
    owner: str
    repo: str

    @classmethod
    def parse(cls, value: str):
        if "/" in value:
            owner, repo = value.split("/")
            return cls(owner=owner, repo=repo)

    def __str__(self) -> str:
        return f"{self.owner}/{self.repo}"


class RepositoryTransformer(Transformer):
    async def transform(self, interaction: Interaction, value: str):
        if result := Repository.parse(value):
            return result

        async with GHUtilsBot.get_github_app_of(interaction) as (github, state):
            if state != LoginState.LOGGED_IN:
                raise ValueError(
                    f"Value does not contain '/' and user is not logged in: {value}"
                )

            user = await gh_request(github.rest.users.async_get_authenticated())
            return Repository(owner=user.login, repo=value)


RepositoryParam = Transform[Repository, RepositoryTransformer]


class ReferenceTransformer[T](Transformer, ABC):
    @property
    @abstractmethod
    def separator(self) -> str: ...

    @property
    @abstractmethod
    def reference_pattern(self) -> str: ...

    @abstractmethod
    async def resolve_reference(
        self,
        github: GitHub[Any],
        repo: Repository,
        reference: str,
    ) -> T: ...

    @abstractmethod
    async def search_for_autocomplete(
        self,
        github: GitHub[Any],
        repo: Repository,
        search: str,
    ) -> Iterable[tuple[str, str]]:
        """Returns a list of `(reference, description)`.

        For example, issues would return a list of `(issue_number, issue_title)`.
        """

    async def transform(
        self,
        interaction: Interaction,
        value: str,
    ) -> T:
        repo, raw_reference = self.split_raw_value(interaction, value)

        match = re.match(rf"^({self.reference_pattern})", raw_reference)
        if not match:
            raise ValueError(f"Invalid reference: {raw_reference}")

        async with GHUtilsBot.get_github_app_of(interaction) as (github, _):
            return await self.resolve_reference(github, repo, match[1])

    async def autocomplete(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        interaction: Interaction,
        value: str,
    ) -> list[Choice[str]]:
        try:
            repo, search = self.split_raw_value(interaction, value)
        except ValueError:
            return []

        async with GHUtilsBot.get_github_app_of(interaction) as (github, state):
            match state:
                case LoginState.LOGGED_IN:
                    error = None
                case LoginState.LOGGED_OUT:
                    error = "⚠️ Log in with `/gh login` to enable autocomplete."
                case LoginState.EXPIRED:
                    error = "⚠️ Session expired. Log back in with `/gh login` to reenable autocomplete."
            if error:
                return [Choice(name=error, value=value)]

            return [
                self.build_choice(repo, reference, description)
                for reference, description in await self.search_for_autocomplete(
                    github, repo, search
                )
            ]

    def split_raw_value(
        self,
        interaction: Interaction,
        value: str,
    ) -> tuple[Repository, str]:
        if self.separator in value:
            raw_repo, rest = value.split(self.separator, maxsplit=1)
        else:
            raw_repo = ""
            rest = value

        if not raw_repo:
            # TODO: get default repo from user settings
            raise ValueError(f"Missing username and repository: {value}")

        if not (repo := Repository.parse(raw_repo)):
            raise ValueError(f"Missing '/' between username and repository: {value}")

        return repo, rest

    def build_choice(
        self,
        repo: Repository,
        reference: str,
        description: str,
    ) -> Choice[str]:
        value = f"{repo}{self.separator}{reference}"
        name = truncate_str(
            f"{value}: {description}",
            limit=100,
            message="...",
        )
        return Choice(name=name, value=value)


@dataclass(kw_only=True)
class IssueReferenceTransformer(ReferenceTransformer[Issue]):
    issue_type: Literal["issue", "pr"]

    @property
    def separator(self):
        return "#"

    @property
    def reference_pattern(self):
        return r"\d+"

    async def resolve_reference(
        self,
        github: GitHub[Any],
        repo: Repository,
        reference: str,
    ) -> Issue:
        # FIXME: handle GitHubException
        return await gh_request(
            github.rest.issues.async_get(
                owner=repo.owner,
                repo=repo.repo,
                issue_number=int(reference),
            )
        )

    async def search_for_autocomplete(
        self,
        github: GitHub[Any],
        repo: Repository,
        search: str,
    ) -> list[tuple[str, str]]:
        try:
            results = await gh_request(
                github.rest.search.async_issues_and_pull_requests(
                    f"{search} is:{self.issue_type} repo:{repo}",
                    per_page=25,
                )
            )
        except RequestFailed:
            return []
        except GitHubException as e:
            logger.info(e)
            return []
        return [(str(result.number), result.title) for result in results.items]


IssueParam = Transform[Issue, IssueReferenceTransformer(issue_type="issue")]

PullRequestParam = Transform[PullRequest, IssueReferenceTransformer(issue_type="pr")]


@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
class GitHubCog(GHUtilsCog, GroupCog, group_name="gh"):
    """GitHub-related commands."""

    # /gh

    @app_commands.command()
    async def issue(self, interaction: Interaction, issue: IssueParam):
        """Get a link to a GitHub issue."""

        await interaction.response.send_message(f"#{issue.number}: {issue.title}")

    @app_commands.command()
    async def pr(self, interaction: Interaction, pr: PullRequestParam):
        """Get a link to a GitHub pull request."""

        await interaction.response.send_message(f"#{pr.number}: {pr.title}")

    @app_commands.command()
    async def commit(self, interaction: Interaction):
        """Get a link to a GitHub commit."""

        await interaction.response.defer(ephemeral=False)

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

    # /gh list

    gh_list = Group(
        name="list",
        description="Commands to list values from GitHub.",
    )

    @gh_list.command()
    async def issues(
        self,
        interaction: Interaction,
        repo: RepositoryParam,
    ):
        async with self.bot.get_github_app(interaction) as (github, _):
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
