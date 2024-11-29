"""Localization helpers."""

import re
from typing import Mapping

from discord import app_commands
from discord.app_commands import locale_str

type StrIterable = list[str] | tuple[str, ...]

_SEPARATOR_PATTERN = re.compile(r"[ _-]+")


def command_description(command: str):
    command = _format_command(command)
    return locale_str(f"command-description_{command}")


def parameter_description(command: str | None, parameter: str):
    command = _format_command(command or "common")
    return locale_str(f"parameter-description_{command}_{parameter}")


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


def _format_command(command: str):
    return _SEPARATOR_PATTERN.sub("-", command).replace("/", "")
