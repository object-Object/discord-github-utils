import logging
import sys
from dataclasses import dataclass
from typing import Any, Self, cast

from discord.ext.commands import Cog, CogMeta

from .bot import GHUtilsBot

logger = logging.getLogger(__name__)


class BaseCogMeta(CogMeta):
    def __new__(cls, *args: Any, **kwargs: Any) -> CogMeta:
        if "name" not in kwargs:
            name = cast(str, args[0]).removesuffix("Cog")
            if name:
                kwargs["name"] = name
        return super().__new__(cls, *args, **kwargs)


@dataclass
class BaseCog(Cog, metaclass=BaseCogMeta):
    """Base class for GHUtils cogs.

    When subclasses are defined, a `setup` function (`cls.setup`) is added to the module
    of the subclass. This can be disabled by adding `setup=False` to the class kwargs.
    """

    bot: GHUtilsBot

    def __init_subclass__(cls, setup: bool = True, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if setup:
            module = sys.modules[cls.__module__]
            if not hasattr(module, "setup"):
                setattr(module, "setup", cls.setup)
            else:
                logger.debug(
                    f"Not adding setup function for {cls} to {cls.__module__},"
                    + f" attribute already exists: {getattr(module, "setup", None)}"
                )

    @classmethod
    async def setup(cls, bot: GHUtilsBot):
        await bot.add_cog(cls._create_cog(bot))

    @classmethod
    def _create_cog(cls, bot: GHUtilsBot) -> Self:
        """Factory method called by `setup` when adding this cog to the bot."""
        return cls(bot)

    # required to make the help command not fail
    def __hash__(self) -> int:
        return hash(self.__class__)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BaseCog):
            return self.__class__ == other.__class__
        return super().__eq__(other)
