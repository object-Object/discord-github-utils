from enum import Enum, auto

from discord.app_commands import AppCommandError


class LoginState(Enum):
    LOGGED_IN = auto()
    LOGGED_OUT = auto()
    EXPIRED = auto()


class NotLoggedInError(AppCommandError):
    pass
