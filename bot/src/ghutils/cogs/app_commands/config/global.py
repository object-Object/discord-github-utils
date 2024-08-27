from discord import Interaction, app_commands
from discord.ext.commands import GroupCog

from ghutils.core.cog import GHUtilsCog
from ghutils.db.config import get_user_config
from ghutils.db.models import UserConfig
from ghutils.utils.discord.config import Accessor, ConfigAction
from ghutils.utils.discord.transformers import RepositoryParam
from ghutils.utils.github import Repository


class GlobalConfigCog(GHUtilsCog, GroupCog, group_name="gh_config_global"):
    """Configure settings globally for your account."""

    @app_commands.command()
    async def default_repo(
        self,
        interaction: Interaction,
        action: ConfigAction,
        value: RepositoryParam | None = None,
    ):
        def accessor(config: UserConfig) -> Accessor[Repository | None]:
            config.default_repo = yield config.default_repo

        await action.apply(
            interaction,
            value,
            get_user_config,
            accessor,
            name="default_repo",
            default=None,
            scope_msg="for your account",
        )
