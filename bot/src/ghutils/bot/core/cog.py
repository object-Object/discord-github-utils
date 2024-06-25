import logging
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Awaitable, Self

from discord.ext.commands import Cog

from .bot import GHUtilsBot, GHUtilsContext

logger = logging.getLogger(__name__)


@dataclass
class BaseCog(Cog):
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

    if TYPE_CHECKING:
        # make Pyright allow async cog_check and using GHUtilsContext
        def cog_check(  # pyright: ignore[reportIncompatibleMethodOverride]
            self,
            ctx: GHUtilsContext,
        ) -> bool | Awaitable[bool]: ...
