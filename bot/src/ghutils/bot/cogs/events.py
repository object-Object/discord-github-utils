import logging

from discord import Interaction
from discord.ext.commands import Cog

from ghutils.bot.core import BaseCog
from ghutils.bot.utils.commands import get_command, print_command

logger = logging.getLogger(__name__)


class EventsCog(BaseCog):
    """Cog for event handlers that don't fit anywhere else."""

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
