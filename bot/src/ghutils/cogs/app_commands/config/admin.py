from typing import Literal

from discord import Interaction, app_commands
from discord.ext.commands import GroupCog
from sqlalchemy.exc import InvalidRequestError

from ghutils.core.cog import GHUtilsCog, SubGroup
from ghutils.db.config import get_guild_config
from ghutils.utils.discord.transformers import RepositoryParam

type ServerConfigOption = Literal[
    "default_repo",
    "all",
]


@app_commands.guild_only()
@app_commands.default_permissions(manage_guild=True)
class AdminConfigCog(GHUtilsCog, GroupCog, group_name="gh_admin_config"):
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
            value: RepositoryParam,
        ):
            with self.bot.db_session() as session:
                config = get_guild_config(session, interaction)
                old_value = config.default_repo
                config.default_repo = value
                session.add(config)
                session.commit()

                if old_value:
                    message = f"✅ Changed **default_repo** from `{old_value}` to `{value}` for this server."
                else:
                    message = f"✅ Set **default_repo** to `{value}` for this server."

                await interaction.response.send_message(message, ephemeral=True)