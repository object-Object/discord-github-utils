from enum import Enum
from typing import Callable, Generator

from discord import Interaction
from sqlmodel import Session, SQLModel

from ghutils.core.bot import GHUtilsBot
from ghutils.utils.generators import send_final

type Accessor[T] = Generator[T, T, None]


class ConfigAction(Enum):
    get = "get"
    set = "set"
    reset = "reset"

    async def apply[C: SQLModel, V](
        self,
        interaction: Interaction,
        value: V,
        get_config: Callable[[Session, Interaction], C],
        accessor: Callable[[C], Accessor[V]],
        *,
        name: str,
        default: V,
        scope_msg: str,
    ):
        with GHUtilsBot.db_session_of(interaction) as session:
            config = get_config(session, interaction)
            generator = accessor(config)

            match self:
                case ConfigAction.get:
                    await interaction.response.send_message(
                        f"ℹ️ **{name}** is currently set to `{next(generator)}` {scope_msg}.",
                        ephemeral=True,
                    )

                case ConfigAction.set:
                    await self._set_value(
                        interaction,
                        session,
                        config,
                        generator,
                        new=value,
                        failure_msg=f"⚠️ **{name}** is already set to `{{old}}` {scope_msg}.",
                        success_msg=f"✅ Set **{name}** to `{{new}}` {scope_msg} (was `{{old}}`).",
                    )

                case ConfigAction.reset:
                    await self._set_value(
                        interaction,
                        session,
                        config,
                        generator,
                        new=default,
                        failure_msg=f"⚠️ **{name}** is already set to the default value (`{{old}}`) {scope_msg}.",
                        success_msg=f"✅ Reset **{name}** to `{{new}}` {scope_msg} (was `{{old}}`).",
                    )

    async def _set_value[V](
        self,
        interaction: Interaction,
        session: Session,
        config: SQLModel,
        generator: Accessor[V],
        *,
        new: V,
        failure_msg: str,
        success_msg: str,
    ):
        old = next(generator)

        if old == new:
            await interaction.response.send_message(
                failure_msg.format(old=old),
                ephemeral=True,
            )
            return

        send_final(generator, new)
        session.add(config)
        session.commit()

        await interaction.response.send_message(
            success_msg.format(old=old, new=new),
            ephemeral=True,
        )
