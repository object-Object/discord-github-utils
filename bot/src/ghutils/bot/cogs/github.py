from discord import Interaction, app_commands
from discord.ext.commands import GroupCog

from ghutils.bot.core import BaseCog


@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
class GitHubCog(BaseCog, GroupCog, group_name="gh"):
    """GitHub-related commands."""

    @app_commands.command()
    async def issue(self, interaction: Interaction):
        """Get a link to a GitHub issue."""

        await interaction.response.defer(ephemeral=False)

    @app_commands.command()
    async def pr(self, interaction: Interaction):
        """Get a link to a GitHub pull request."""

        await interaction.response.defer(ephemeral=False)

    @app_commands.command()
    async def commit(self, interaction: Interaction):
        """Get a link to a GitHub commit."""

        await interaction.response.defer(ephemeral=False)
