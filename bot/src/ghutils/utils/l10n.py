"""Localization helpers."""

import logging
import re
from typing import Any

from discord import Interaction
from discord.app_commands import locale_str

type StrIterable = list[str] | tuple[str, ...]

_SEPARATOR_PATTERN = re.compile(r"[ _-]+")


logger = logging.getLogger(__name__)


async def translate_text(interaction: Interaction, key: str, **kwargs: Any):
    if interaction.command is None:
        raise ValueError(
            "Attempted to translate command text when interaction.command is None"
        )

    msg_id = command_text_id(interaction.command.qualified_name, key)
    result = await interaction.translate(locale_str(msg_id, **kwargs))

    if result is None:
        logger.warning(f"Failed to translate string: {msg_id}")
        return msg_id

    return result


def command_description_id(command: str):
    command = _format_identifier(command)
    return f"{command}_description"


def command_description(command: str):
    return locale_str("...", id=command_description_id(command))


def parameter_description_id(command: str | None, parameter: str):
    command = _format_identifier(command or "common")
    parameter = _format_identifier(parameter)
    return f"{command}_parameter-description_{parameter}"


def parameter_description(command: str | None, parameter: str):
    return locale_str("...", id=parameter_description_id(command, parameter))


def command_text_id(command: str, key: str):
    command = _format_identifier(command)
    return f"{command}_text_{key}"


def _format_identifier(command: str):
    return _SEPARATOR_PATTERN.sub("-", command).replace("/", "")
