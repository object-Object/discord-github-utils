from enum import Enum, auto
from typing import Any

from discord.app_commands import AppCommandError


class LoginState(Enum):
    LOGGED_IN = auto()
    LOGGED_OUT = auto()
    EXPIRED = auto()


# TODO: add Literal[LoginState.LOGGED_OUT, LoginState.EXPIRED] parameter
class NotLoggedInError(AppCommandError):
    """An exception raised when the command user is not logged in to GitHub.

    Commands that require the user of the command to log in with GitHub can throw this
    if the user is not logged in to reply with a standard error message.
    """


class SilentError(AppCommandError):
    """Base class for exceptions that should be silently caught and ignored."""


class InvalidInputError(AppCommandError):
    """An exception raised within command handlers when an input value is invalid.

    Displays a similar error message as `TransformerError`.
    """

    def __init__(self, value: Any, message: str):
        self.value = value
        self.message = message
        super().__init__(f"{message} (value: {value})")
