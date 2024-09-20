from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, cast, overload

from discord import Interaction
from sqlmodel import Session

from ghutils.utils.github import RepositoryName

from .models import GuildConfig, UserConfig, UserGuildConfig


@dataclass
class GlobalConfigs:
    user: UserConfig

    @property
    def default_repo(self) -> RepositoryName | None:
        return self.user.default_repo


@dataclass
class GuildConfigs(GlobalConfigs):
    user_guild: UserGuildConfig
    guild: GuildConfig

    @property
    def default_repo(self) -> RepositoryName | None:
        return self.user_guild.default_repo or self.guild.default_repo


@overload
def get_configs(
    session: Session,
    interaction: Interaction,
) -> GlobalConfigs | GuildConfigs: ...


@overload
def get_configs(
    session: Session,
    interaction: Interaction,
    guild_id: int,
) -> GuildConfigs: ...


def get_configs(
    session: Session,
    interaction: Interaction,
    guild_id: int | None = None,
) -> GlobalConfigs | GuildConfigs:
    guild_id = guild_id or interaction.guild_id

    if not guild_id:
        return GlobalConfigs(
            user=get_user_config(session, interaction),
        )

    return GuildConfigs(
        user=get_user_config(session, interaction),
        user_guild=get_user_guild_config(session, interaction),
        guild=get_guild_config(session, interaction),
    )


def get_user_config(session: Session, interaction: Interaction):
    return _get_or_create(
        session,
        UserConfig,
        user_id=interaction.user.id,
    )


def get_user_guild_config(session: Session, interaction: Interaction):
    if not interaction.guild_id:
        raise ValueError("get_user_guild_config can only be used in a guild")
    return _get_or_create(
        session,
        UserGuildConfig,
        user_id=interaction.user.id,
        guild_id=interaction.guild_id,
    )


def get_guild_config(session: Session, interaction: Interaction):
    if not interaction.guild_id:
        raise ValueError("get_guild_config can only be used in a guild")
    return _get_or_create(
        session,
        GuildConfig,
        guild_id=interaction.guild_id,
    )


def _get_or_create[**P, T](
    session: Session,
    model_type: Callable[P, T] | type[T],
    *args: P.args,
    **kwargs: P.kwargs,
) -> T:
    model_cls = cast(type[T], model_type)
    return session.get(model_cls, kwargs) or model_cls(*args, **kwargs)
