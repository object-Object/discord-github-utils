import logging

from discord import Interaction
from discord.ext.commands import Cog

from ghutils.core.cog import GHUtilsCog
from ghutils.utils.discord.commands import get_command, print_command
from ghutils.utils.discord.components import (
    RefreshCommitButton,
    RefreshIssueButton,
    RefreshIssuesButton,
)
from ghutils.utils.discord.visibility import PermanentDeleteButton

logger = logging.getLogger(__name__)


class EventsCog(GHUtilsCog):
    """Cog for event handlers that don't fit anywhere else."""

    @Cog.listener()
    async def on_ready(self):
        logger.info(f"Logged in as {self.bot.user}")
        self.bot.add_dynamic_items(
            PermanentDeleteButton,
            RefreshCommitButton,
            RefreshIssueButton,
            RefreshIssuesButton,
        )
        await self.bot.fetch_custom_emojis()

    @Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        if command := get_command(interaction):
            logger.debug(
                f"Command executed: {
                    print_command(interaction, command, truncate=False)
                }"
            )
