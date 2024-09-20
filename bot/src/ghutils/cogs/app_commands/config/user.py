from contextlib import contextmanager
from typing import Any, Literal

from discord import Color, Embed, Interaction, app_commands
from discord.ext.commands import GroupCog
from sqlalchemy.exc import InvalidRequestError
from sqlmodel import Session

from ghutils.core.cog import GHUtilsCog, SubGroup
from ghutils.db.config import get_user_config, get_user_guild_config
from ghutils.utils.discord.transformers import RepositoryNameOption

type UserConfigOption = Literal[
    "default_repo",
    "all",
]


class UserConfigCog(GHUtilsCog, GroupCog, group_name="gh_config"):
    """View or change config options for your account."""

    @app_commands.command()
    async def get(self, interaction: Interaction):
        """View the current value of config options for your account."""

        with self.bot.db_session() as session:
            embeds = list[Embed]()

            user_config = get_user_config(session, interaction)
            user_embed = Embed(
                title="Global Config",
                description="Config options for your account in all servers and/or in DMs, depending on the option.",
                color=Color.blue(),
            )
            _add_config_options(
                user_embed,
                ("default_repo", user_config.default_repo),
            )
            embeds.append(user_embed)

            if interaction.guild:
                guild_config = get_user_guild_config(session, interaction)
                guild_embed = Embed(
                    title="Local Config",
                    description="Config options for your account in this server.",
                    color=Color.blue(),
                )
                _add_config_options(
                    guild_embed,
                    ("default_repo", guild_config.default_repo),
                )
                embeds.append(guild_embed)

            await interaction.response.send_message(embeds=embeds, ephemeral=True)

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
            value: RepositoryNameOption,
        ):
            with self._update_config(interaction) as config:
                old_value = config.default_repo
                config.default_repo = value
            await _send_updated(interaction, "default_repo", old_value, value)

        @contextmanager
        def _update_config(self, interaction: Interaction):
            with self.bot.db_session() as session:
                config = _get_config(session, interaction)
                yield config
                session.add(config)
                session.commit()


async def _send_updated[T](interaction: Interaction, name: str, old: T | None, new: T):
    if interaction.guild:
        scope = "this server"
    else:
        scope = "DMs"

    if old:
        message = f"✅ Changed **{name}** from `{old}` to `{new}` in {scope} for your account."
    else:
        message = f"✅ Set **{name}** to `{new}` in {scope} for your account."

    await interaction.response.send_message(message, ephemeral=True)


def _add_config_options(embed: Embed, *options: tuple[str, Any]):
    for name, value in options:
        embed.add_field(name=name, value=f"`{value}`", inline=False)
    return embed


def _get_config(session: Session, interaction: Interaction):
    if interaction.guild_id:
        return get_user_guild_config(session, interaction)
    else:
        return get_user_config(session, interaction)
