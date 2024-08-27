from discord import Interaction, app_commands
from discord.ext.commands import GroupCog

from ghutils.core.cog import GHUtilsCog
from ghutils.db.config import get_guild_config
from ghutils.db.models import GuildConfig
from ghutils.utils.discord.config import Accessor, ConfigAction
from ghutils.utils.discord.transformers import RepositoryParam
from ghutils.utils.github import Repository


@app_commands.guild_only()
@app_commands.default_permissions(manage_guild=True)
class AdminConfigCog(GHUtilsCog, GroupCog, group_name="gh_config_admin"):
    """Configure settings for everyone who uses the bot in this server."""

    @app_commands.command()
    async def default_repo(
        self,
        interaction: Interaction,
        action: ConfigAction,
        value: RepositoryParam | None = None,
    ):
        def accessor(config: GuildConfig) -> Accessor[Repository | None]:
            config.default_repo = yield config.default_repo

        assert interaction.guild
        await action.apply(
            interaction,
            value,
            get_guild_config,
            accessor,
            name="default_repo",
            default=None,
            scope_msg=f"for **{interaction.guild.name}**",
        )
