from enum import Enum, auto

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
