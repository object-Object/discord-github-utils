import logging

from discord import Interaction
from discord.ext.commands import Cog

from ghutils_bot.core import BaseCog
from ghutils_bot.utils.commands import get_command, print_command

logger = logging.getLogger(__name__)


class EventsCog(BaseCog):
    @Cog.listener()
    async def on_ready(self):
        logger.info(f"Logged in as {self.bot.user}")

    @Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        if command := get_command(interaction):
            logger.debug(
                f"Command executed: {
                    print_command(interaction, command, truncate=False)
                }"
            )
