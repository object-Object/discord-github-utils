from discord import Interaction, app_commands
from discord.ext.commands import GroupCog

from ghutils.core.cog import GHUtilsCog
from ghutils.db.config import get_user_guild_config
from ghutils.db.models import UserGuildConfig
from ghutils.utils.discord.config import Accessor, ConfigAction
from ghutils.utils.discord.transformers import RepositoryParam
from ghutils.utils.github import Repository


@app_commands.guild_only()
class LocalConfigCog(GHUtilsCog, GroupCog, group_name="gh_config_local"):
    """Configure settings for your account in this server."""

    @app_commands.command()
    async def default_repo(
        self,
        interaction: Interaction,
        action: ConfigAction,
        value: RepositoryParam | None = None,
    ):
        def accessor(config: UserGuildConfig) -> Accessor[Repository | None]:
            config.default_repo = yield config.default_repo

        assert interaction.guild
        await action.apply(
            interaction,
            value,
            get_user_guild_config,
            accessor,
            name="default_repo",
            default=None,
            scope_msg=f"in **{interaction.guild.name}** for your account",
        )
