from enum import Enum, auto


class LoginState(Enum):
    LOGGED_IN = auto()
    LOGGED_OUT = auto()
    EXPIRED = auto()
