from __future__ import annotations

import logging
import re
import uuid
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any, Callable, Iterable, Literal, cast, overload

from discord import Interaction, app_commands
from discord.app_commands import Choice, Transform, Transformer
from discord.ext.commands import GroupCog
from discord.ui import Button, View
from githubkit import GitHub, Response
from githubkit.exception import GitHubException, RequestFailed
from githubkit.rest import Commit, Issue, PullRequest
from sqlmodel import Session

from ghutils.bot.core import GHUtilsCog
from ghutils.bot.core.bot import GHUtilsBot
from ghutils.bot.core.cog import SubGroup
from ghutils.bot.core.types import LoginState
from ghutils.bot.db.models import (
    UserGitHubTokens,
    UserGlobalConfig,
    UserGuildConfig,
    UserLogin,
)
from ghutils.bot.utils.github import Repository, gh_request
from ghutils.bot.utils.strings import truncate_str

logger = logging.getLogger(__name__)


class ConfigScope(Enum):
    GLOBAL = auto()
    GUILD = auto()


class RepositoryTransformer(Transformer):
    async def transform(self, interaction: Interaction, value: str):
        if result := Repository.parse(value):
            return result

        async with GHUtilsBot.github_app_of(interaction) as (github, state):
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
    ) -> Iterable[tuple[str | int, str]]:
        """Returns a list of `(reference, description)`.

        For example, issues would return a list of `(issue_number, issue_title)`.
        """

    async def transform(
        self,
        interaction: Interaction,
        value: str,
    ) -> T:
        repo, raw_reference = await self.get_repo_and_reference(interaction, value)

        match = re.match(rf"^({self.reference_pattern})", raw_reference)
        if not match:
            raise ValueError(f"Malformed reference: {raw_reference}")

        async with GHUtilsBot.github_app_of(interaction) as (github, _):
            try:
                return await self.resolve_reference(github, repo, match[1])
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
            match state:
                case LoginState.LOGGED_IN:
                    error = None
                case LoginState.LOGGED_OUT:
                    error = "⚠️ Log in with `/gh login` to enable autocomplete."
                case LoginState.EXPIRED:
                    error = "⚠️ Session expired. Log back in with `/gh login` to reenable autocomplete."
            if error:
                return [Choice(name=error, value=value)]

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
    ) -> tuple[Repository, str]:
        if self.separator in value:
            raw_repo, rest = value.split(self.separator, maxsplit=1)
        else:
            raw_repo = ""
            rest = value

        if not raw_repo:
            with GHUtilsBot.db_session_of(interaction) as session:
                config = await _get_config(interaction, session, scope=None)
                if repo := config.default_repo:
                    return repo, rest
            raise ValueError(f"Missing username and repository: {value}")

        if not (repo := Repository.parse(raw_repo)):
            raise ValueError(f"Missing '/' between username and repository: {value}")

        return repo, rest

    def build_choice(
        self,
        repo: Repository,
        reference: str | int,
        description: str,
    ) -> Choice[str]:
        value = f"{repo}{self.separator}{reference}"
        name = truncate_str(
            f"{value}: {description}",
            limit=100,
            message="...",
        )
        return Choice(name=name, value=value)


class IssueOrPRReferenceTransformer[T](ReferenceTransformer[T]):
    @property
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
        repo: Repository,
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
    def issue_type(self):
        return "issue"

    async def resolve_reference(
        self,
        github: GitHub[Any],
        repo: Repository,
        reference: str,
    ) -> Issue:
        return await gh_request(
            github.rest.issues.async_get(
                owner=repo.owner,
                repo=repo.repo,
                issue_number=int(reference),
            )
        )


class PullRequestReferenceTransformer(IssueOrPRReferenceTransformer[PullRequest]):
    @property
    def issue_type(self):
        return "pr"

    async def resolve_reference(
        self,
        github: GitHub[Any],
        repo: Repository,
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
    def reference_pattern(self):
        return r"[0-9a-f]{5,40}"

    async def resolve_reference(
        self,
        github: GitHub[Any],
        repo: Repository,
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
        repo: Repository,
        search: str,
    ) -> list[tuple[str | int, str]]:
        results = await gh_request(
            github.rest.search.async_commits(
                f"{search} repo:{repo}",
                per_page=25,
            )
        )
        return [
            (result.sha[:12], result.commit.message.split("\n")[0])
            for result in results.items
        ]


IssueParam = Transform[Issue, IssueReferenceTransformer]

PullRequestParam = Transform[PullRequest, PullRequestReferenceTransformer]

CommitParam = Transform[Commit, CommitReferenceTransformer]


@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
class GitHubCog(GHUtilsCog, GroupCog, group_name="gh"):
    """GitHub-related commands."""

    # /gh

    @app_commands.command()
    async def issue(self, interaction: Interaction, issue: IssueParam):
        """Get a link to a GitHub issue."""

        await interaction.response.send_message(
            f"[#{issue.number}](<{issue.html_url}>): {issue.title}"
        )

    @app_commands.command()
    async def pr(self, interaction: Interaction, pr: PullRequestParam):
        """Get a link to a GitHub pull request."""

        await interaction.response.send_message(
            f"[#{pr.number}](<{pr.html_url}>): {pr.title}"
        )

    @app_commands.command()
    async def commit(self, interaction: Interaction, commit: CommitParam):
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

    class Config(SubGroup):
        """Configure the behaviour of the bot."""

        @app_commands.command()
        async def default_repo(
            self,
            interaction: Interaction,
            repo: RepositoryParam | None,
            scope: ConfigScope | None,
        ):
            """Set or clear the default repository for commands such as `/gh issue`."""

            with self.bot.db_session() as session:
                if config := await _get_config(interaction, session, scope):
                    old_value = config.default_repo
                    if old_value == repo:
                        if repo:
                            message = f"default_repo is already `{repo}`."
                        else:
                            message = "default_repo is already unset."
                        await interaction.response.send_message(
                            f"❌ {message}",
                            ephemeral=True,
                        )
                        return

                    config.default_repo = repo
                    session.add(config)
                    session.commit()

                    if not repo:
                        message = f"Unset default_repo (was `{old_value}`)."
                    elif old_value:
                        message = (
                            f"Changed default repo from `{old_value}` to `{repo}`."
                        )
                    else:
                        message = f"Set default_repo to `{repo}`."
                    await interaction.response.send_message(
                        f"✅ {message}",
                        ephemeral=True,
                    )


@overload
async def _get_config(
    interaction: Interaction,
    session: Session,
    scope: Literal[ConfigScope.GLOBAL],
) -> UserGlobalConfig: ...


@overload
async def _get_config(
    interaction: Interaction,
    session: Session,
    scope: Literal[ConfigScope.GUILD],
) -> UserGuildConfig | None: ...


@overload
async def _get_config(
    interaction: Interaction,
    session: Session,
    scope: None,
) -> UserGlobalConfig | UserGuildConfig: ...


@overload
async def _get_config(
    interaction: Interaction,
    session: Session,
    scope: ConfigScope,
) -> UserGlobalConfig | UserGuildConfig | None: ...


async def _get_config(
    interaction: Interaction,
    session: Session,
    scope: ConfigScope | None,
) -> UserGlobalConfig | UserGuildConfig | None:
    user_id = interaction.user.id
    guild_id = interaction.guild_id
    match scope:
        case ConfigScope.GUILD | None if guild_id is not None:
            return _get_or_create(
                session,
                UserGuildConfig,
                user_id=user_id,
                guild_id=guild_id,
            )
        case ConfigScope.GUILD:
            await interaction.response.send_message(
                "❌ Cannot set per-guild config options outside of a guild.",
                ephemeral=True,
            )
            return
        case ConfigScope.GLOBAL | None:
            return _get_or_create(
                session,
                UserGlobalConfig,
                user_id=user_id,
            )


def _get_or_create[**P, T](
    session: Session,
    model_type: Callable[P, T] | type[T],
    *args: P.args,
    **kwargs: P.kwargs,
) -> T:
    assert isinstance(model_type, type)
    model_type = cast(type[T], model_type)
    return session.get(model_type, kwargs) or model_type(*args, **kwargs)


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
