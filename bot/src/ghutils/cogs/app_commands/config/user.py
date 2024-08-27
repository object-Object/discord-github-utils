from typing import Literal

from discord import Interaction, app_commands
from discord.ext.commands import GroupCog
from sqlalchemy.exc import InvalidRequestError
from sqlmodel import Session

from ghutils.core.cog import GHUtilsCog, SubGroup
from ghutils.db.config import get_user_config, get_user_guild_config
from ghutils.utils.discord.transformers import RepositoryParam

type UserConfigOption = Literal[
    "default_repo",
    "all",
]


class UserConfigCog(GHUtilsCog, GroupCog, group_name="gh_config"):
    """View or change config options for your account."""

    @app_commands.command()
    async def get(
        self,
        interaction: Interaction,
        option: UserConfigOption = "all",
    ):
        """View the current value of config options for your account."""

        with self.bot.db_session() as session:
            config = _get_config(session, interaction)
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
        option: UserConfigOption,
    ):
        """Reset config options for your account to the default value."""

        with self.bot.db_session() as session:
            config = _get_config(session, interaction)

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
        """Change the value of config options for your account."""

        @app_commands.command()
        async def default_repo(
            self,
            interaction: Interaction,
            value: RepositoryParam,
        ):
            with self.bot.db_session() as session:
                config = _get_config(session, interaction)
                old_value = config.default_repo
                config.default_repo = value
                session.add(config)
                session.commit()

                if interaction.guild:
                    scope = f"**{interaction.guild.name}**"
                else:
                    scope = "DMs"

                if old_value:
                    message = f"✅ Changed **default_repo** from `{old_value}` to `{value}` in {scope} for your account."
                else:
                    message = f"✅ Set **default_repo** to `{value}` in {scope} for your account."

                await interaction.response.send_message(message, ephemeral=True)


def _get_config(session: Session, interaction: Interaction):
    if interaction.guild_id:
        return get_user_guild_config(session, interaction)
    else:
        return get_user_config(session, interaction)
