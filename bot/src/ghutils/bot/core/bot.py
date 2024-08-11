import logging
from dataclasses import dataclass

from discord import Game, Intents, Interaction
from discord.ext import commands
from discord.ext.commands import Bot, Context, NoEntryPointError
from github import Github
from sqlmodel import Session, create_engine

from ghutils.bot import cogs
from ghutils.bot.db.models import UserGitHubTokens
from ghutils.bot.utils.imports import iter_modules

from .env import GHUtilsEnv
from .types import LoginResult

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

    def get_github_app(self, user_id: int | Interaction) -> tuple[Github, LoginResult]:
        match user_id:
            case int():
                pass
            case Interaction(user=user):
                user_id = user.id

        oauth = self.env.github.get_oauth_application()

        with self.db_session() as session:
            user_tokens = session.get(UserGitHubTokens, user_id)

            if user_tokens is None:
                return self._get_default_installation_app(), LoginResult.LOGGED_OUT

            if user_tokens.is_refresh_expired():
                return self._get_default_installation_app(), LoginResult.EXPIRED

            # authenticate on behalf of the user
            token = user_tokens.get_token(oauth)
            auth = oauth.get_app_user_auth(token)

            # update stored credentials if the current ones expired
            if auth.token != user_tokens.token:
                user_tokens.refresh(auth)
                session.add(user_tokens)
                session.commit()

            return Github(auth=auth), LoginResult.LOGGED_IN

    def _get_default_installation_app(self):
        return Github(auth=self.env.github.get_default_installation_auth())
