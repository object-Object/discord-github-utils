"""Localization helpers."""

import re
from typing import Mapping

from discord import app_commands
from discord.app_commands import locale_str

type StrIterable = list[str] | tuple[str, ...]

_SEPARATOR_PATTERN = re.compile(r"[ _-]+")


def command_description_id(command: str):
    command = _format_identifier(command)
    return f"command-description_{command}"


def command_description(command: str):
    return locale_str("...", id=command_description_id(command))


def parameter_description_id(command: str | None, parameter: str):
    command = _format_identifier(command or "common")
    parameter = _format_identifier(parameter)
    return f"parameter-description_{command}_{parameter}"


def parameter_description(command: str | None, parameter: str):
    return locale_str("...", id=parameter_description_id(command, parameter))


def describe_common(*parameters: str):
    return describe(common=parameters)


def describe(
    dict_args: Mapping[str, StrIterable] | None = None,
    **kwargs: StrIterable,
):
    """Localize app command parameters.

    Key: command to localize parameters for.

    Value: parameter names.
    """
    if dict_args:
        kwargs |= dict_args
    return app_commands.describe(**{
        parameter: parameter_description(command, parameter)
        for command, parameters in kwargs.items()
        for parameter in parameters
    })


def _format_identifier(command: str):
    return _SEPARATOR_PATTERN.sub("-", command).replace("/", "")
