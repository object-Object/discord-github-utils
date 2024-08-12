import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass

from discord import Game, Intents, Interaction
from discord.ext import commands
from discord.ext.commands import Bot, Context, NoEntryPointError
from githubkit import GitHub
from sqlmodel import Session, create_engine

from ghutils.bot import cogs
from ghutils.bot.db.models import UserGitHubTokens
from ghutils.bot.utils.imports import iter_modules

from .env import GHUtilsEnv
from .types import LoginState

logger = logging.getLogger(__name__)

COGS_MODULE = cogs.__name__

GHUtilsContext = Context["GHUtilsBot"]

GHUtilsInteraction = Interaction["GHUtilsBot"]


@dataclass
class GHUtilsBot(Bot):
    env: GHUtilsEnv

    def __post_init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=Intents.default(),
            activity=Game(f"version {self.env.commit} ({self.env.commit_date})"),
        )
        self.engine = create_engine(self.env.db_url)

    @classmethod
    def of(cls, interaction: Interaction):
        bot = interaction.client
        assert isinstance(bot, cls)
        return bot

    async def load_cogs(self):
        for cog in iter_modules(cogs, skip_internal=True):
            try:
                logger.info(f"Loading extension: {cog}")
                await self.load_extension(cog)
            except NoEntryPointError:
                logger.warning(f"No entry point found: {cog}")
        logger.info("Loaded cogs: " + ", ".join(self.cogs.keys()))

    def db_session(self, expire_on_commit: bool = False):
        return Session(
            self.engine,
            expire_on_commit=expire_on_commit,
        )

    @asynccontextmanager
    async def get_github_app(self, user_id: int | Interaction):
        match user_id:
            case int():
                pass
            case Interaction(user=user):
                user_id = user.id

        with self.db_session() as session:
            user_tokens = session.get(UserGitHubTokens, user_id)

        if user_tokens is None:
            async with self._get_default_installation_app() as github:
                yield github, LoginState.LOGGED_OUT
            return

        if user_tokens.is_refresh_expired():
            async with self._get_default_installation_app() as github:
                yield github, LoginState.EXPIRED
            return

        # authenticate on behalf of the user
        auth = self.env.gh.get_user_auth(user_tokens)
        async with GitHub(auth) as github:
            yield github, LoginState.LOGGED_IN

        # update stored credentials if the current ones were expired
        # NOTE: we need to do this after yielding because there doesn't seem to be a
        # way to force it to refresh if necessary; that happens in the request flow
        if auth.token != user_tokens.token:
            with self.db_session() as session:
                user_tokens.refresh(auth)
                session.add(user_tokens)
                session.commit()

    def _get_default_installation_app(self):
        return GitHub(self.env.gh.get_default_installation_auth())
