import logging
from dataclasses import dataclass

from discord import Game, Intents
from discord.ext import commands
from discord.ext.commands import Bot, NoEntryPointError

from ghutils_bot import cogs
from ghutils_bot.utils.imports import iter_modules

from .env import EnvSettings

logger = logging.getLogger(__name__)


@dataclass
class GHUtilsBot(Bot):
    env: EnvSettings

    def __post_init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=Intents.default(),
            activity=Game(f"version {self.env.commit} ({self.env.commit_date})"),
        )

    async def load_cogs(self):
        for cog in iter_modules(cogs, skip_internal=True):
            try:
                logger.info(f"Loading cog: {cog}")
                await self.load_extension(cog)
            except NoEntryPointError:
                logger.warning(f"No entry point for cog: {cog}")
