from enum import Enum, auto

from typing_extensions import deprecated

from ghutils.resources import get_resource


class LoginState(Enum):
    LOGGED_IN = auto()
    LOGGED_OUT = auto()
    EXPIRED = auto()

    def logged_in(self):
        return self is LoginState.LOGGED_IN

    def logged_out(self):
        return not self.logged_in()


class CustomEmoji(Enum):
    apps_icon = "apps_icon.png"
    nightly_link = "nightly_link.png"

    def __init__(self, filename: str):
        self.filename = filename

    @property
    @deprecated("Use name or filename instead", category=None)
    def value(self):
        return super().value

    def load_image(self) -> bytes:
        return get_resource(f"emoji/{self.filename}").read_bytes()
