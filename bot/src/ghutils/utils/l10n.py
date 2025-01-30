"""Localization helpers."""

import re

from discord.app_commands import locale_str

type StrIterable = list[str] | tuple[str, ...]

_SEPARATOR_PATTERN = re.compile(r"[ _-]+")


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


def _format_identifier(command: str):
    return _SEPARATOR_PATTERN.sub("-", command).replace("/", "")
