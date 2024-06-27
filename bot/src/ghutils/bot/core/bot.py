import logging
from dataclasses import dataclass

from discord import Game, Intents
from discord.ext import commands
from discord.ext.commands import Bot, Context, NoEntryPointError
from sqlmodel import Session, create_engine

from ghutils.bot import cogs
from ghutils.bot.utils.imports import iter_modules

from .env import GHUtilsEnv

logger = logging.getLogger(__name__)

COGS_MODULE = cogs.__name__

GHUtilsContext = Context["GHUtilsBot"]


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
