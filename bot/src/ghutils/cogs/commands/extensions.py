import logging

from discord.ext import commands

from ghutils.core.bot import COGS_MODULE, GHUtilsContext
from ghutils.core.cog import GHUtilsCog
from ghutils.utils.collections import partition
from ghutils.utils.discord.commands import paginate

logger = logging.getLogger(__name__)


class ExtensionsCog(GHUtilsCog):
    """Owner-only message commands for managing cogs/extensions."""

    async def cog_check(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        ctx: GHUtilsContext,
    ) -> bool:
        return await commands.is_owner().predicate(ctx)

    @commands.command(aliases=["exts", "cogs"])
    async def extensions(self, ctx: GHUtilsContext):
        """List all reloadable extensions."""

        cogs, extensions = partition(
            self.bot.extensions.keys(),
            lambda name: name.startswith(COGS_MODULE),
        )

        async with paginate(ctx.reply) as paginator:
            if cogs:
                paginator.add_line("Cogs:")
                for name in cogs:
                    paginator.add_line(f"  {name.removeprefix(COGS_MODULE)}")

            if extensions:
                paginator.add_line("Extensions:")
                for name in extensions:
                    paginator.add_line(f"  {name}")

    @commands.command()
    async def reload(self, ctx: GHUtilsContext, *extensions: str):
        """Reload one or more extensions.

        If no extension names are provided, all extensions will be reloaded.
        """

        if not extensions:
            extensions = tuple(self.bot.extensions.keys())

        for name in extensions:
            logger.info(f"Reloading extension: {name}")
            await self.bot.reload_extension(name, package="ghutils.cogs")

        s = "" if len(extensions) == 1 else "s"
        await ctx.reply(f"Reloaded {len(extensions)} extension{s}.")
