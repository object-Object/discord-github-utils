from enum import Enum, auto


class LoginResult(Enum):
    LOGGED_IN = auto()
    LOGGED_OUT = auto()
    EXPIRED = auto()
