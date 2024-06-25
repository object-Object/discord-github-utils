from typing import Any

from discord import Interaction, InteractionType
from discord.app_commands import Command

AnyCommand = Command[Any, ..., Any]


def get_command(interaction: Interaction) -> AnyCommand | None:
    match interaction.command:
        case Command() as command:
            if interaction.type == InteractionType.application_command:
                return command
        case _:
            pass


def print_command(
    interaction: Interaction,
    command: AnyCommand,
    truncate: bool = True,
) -> str:
    limit = 100 if truncate else None
    args = " ".join(
        f"{name}: {truncate_str(str(value), limit)}"
        for name, value in interaction.namespace
    )
    return f"/{command.qualified_name} {args}"


def truncate_str(text: str, limit: int | None, message: str = " ... (truncated)"):
    if limit is None:
        return text

    limit -= len(message)
    if len(text) <= limit:
        return text

    return text[:limit] + message
