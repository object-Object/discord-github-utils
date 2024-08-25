from __future__ import annotations

from enum import Enum, auto
from typing import Callable, Literal, cast, overload

from discord import Interaction
from sqlmodel import Session

from .models import (
    UserGlobalConfig,
    UserGuildConfig,
)


class ConfigScope(Enum):
    GLOBAL = auto()
    GUILD = auto()


@overload
async def get_config(
    interaction: Interaction,
    session: Session,
    scope: Literal[ConfigScope.GLOBAL],
) -> UserGlobalConfig: ...


@overload
async def get_config(
    interaction: Interaction,
    session: Session,
    scope: Literal[ConfigScope.GUILD],
) -> UserGuildConfig | None: ...


@overload
async def get_config(
    interaction: Interaction,
    session: Session,
    scope: None,
) -> UserGlobalConfig | UserGuildConfig: ...


@overload
async def get_config(
    interaction: Interaction,
    session: Session,
    scope: ConfigScope,
) -> UserGlobalConfig | UserGuildConfig | None: ...


async def get_config(
    interaction: Interaction,
    session: Session,
    scope: ConfigScope | None,
) -> UserGlobalConfig | UserGuildConfig | None:
    user_id = interaction.user.id
    guild_id = interaction.guild_id
    match scope:
        case ConfigScope.GUILD | None if guild_id is not None:
            return _get_or_create(
                session,
                UserGuildConfig,
                user_id=user_id,
                guild_id=guild_id,
            )
        case ConfigScope.GUILD:
            await interaction.response.send_message(
                "❌ Cannot set per-guild config options outside of a guild.",
                ephemeral=True,
            )
            return
        case ConfigScope.GLOBAL | None:
            return _get_or_create(
                session,
                UserGlobalConfig,
                user_id=user_id,
            )


def _get_or_create[**P, T](
    session: Session,
    model_type: Callable[P, T] | type[T],
    *args: P.args,
    **kwargs: P.kwargs,
) -> T:
    assert isinstance(model_type, type)
    model_type = cast(type[T], model_type)
    return session.get(model_type, kwargs) or model_type(*args, **kwargs)
