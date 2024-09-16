from contextlib import contextmanager
from typing import Literal

from discord import Interaction, app_commands
from discord.ext.commands import GroupCog
from sqlalchemy.exc import InvalidRequestError

from ghutils.core.cog import GHUtilsCog, SubGroup
from ghutils.db.config import get_guild_config
from ghutils.utils.discord.transformers import RepositoryOption

type ServerConfigOption = Literal[
    "default_repo",
    "all",
]


@app_commands.guild_only()
@app_commands.default_permissions(manage_guild=True)
class AdminConfigCog(GHUtilsCog, GroupCog, group_name="gh_config_admin"):
    """View or change config options for everyone who uses the bot in this server."""

    @app_commands.command()
    async def get(
        self,
        interaction: Interaction,
        option: ServerConfigOption = "all",
    ):
        """View the current value of config options for this server."""

        with self.bot.db_session() as session:
            config = get_guild_config(session, interaction)
            match option:
                case "all":
                    message = config
                case "default_repo":
                    message = config.default_repo
            await interaction.response.send_message(str(message), ephemeral=True)

    @app_commands.command()
    async def reset(
        self,
        interaction: Interaction,
        option: ServerConfigOption,
    ):
        """Reset config options for this server to the default value."""

        with self.bot.db_session() as session:
            config = get_guild_config(session, interaction)

            if option == "all":
                try:
                    session.delete(config)
                except InvalidRequestError:
                    pass
                else:
                    session.commit()
            else:
                match option:
                    case "default_repo":
                        config.default_repo = None
                session.add(config)
                session.commit()

            await interaction.response.send_message("ok", ephemeral=True)

    class Set(SubGroup):
        """Change the value of config options for this server."""

        @app_commands.command()
        async def default_repo(
            self,
            interaction: Interaction,
            value: RepositoryOption,
        ):
            with self._update_config(interaction) as config:
                old_value = config.default_repo
                config.default_repo = value
            await _send_updated(interaction, "default_repo", old_value, value)

        @contextmanager
        def _update_config(self, interaction: Interaction):
            with self.bot.db_session() as session:
                config = get_guild_config(session, interaction)
                yield config
                session.add(config)
                session.commit()


async def _send_updated[T](interaction: Interaction, name: str, old: T | None, new: T):
    if old:
        message = f"✅ Changed **{name}** from `{old}` to `{new}` for this server."
    else:
        message = f"✅ Set **{name}** to `{new}` for this server."
    await interaction.response.send_message(message, ephemeral=True)
