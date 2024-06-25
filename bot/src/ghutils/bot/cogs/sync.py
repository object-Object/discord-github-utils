from discord.ext import commands

from ghutils.bot.core import GHUtilsCog, GHUtilsContext


class SyncCog(GHUtilsCog):
    """Owner-only message commands for syncing slash commands."""

    async def cog_check(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        ctx: GHUtilsContext,
    ) -> bool:
        return await commands.is_owner().predicate(ctx)

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def sync(self, ctx: GHUtilsContext):
        """Sync guild slash commands to the current guild."""

        assert ctx.guild

        async with ctx.channel.typing():
            self.bot.tree.copy_global_to(guild=ctx.guild)
            await self.bot.tree.sync(guild=ctx.guild)

        await ctx.reply("Synced guild slash commands to this guild.")

    @sync.command()
    @commands.guild_only()
    async def clear(self, ctx: GHUtilsContext):
        """Remove guild slash commands from the current guild."""

        assert ctx.guild

        async with ctx.channel.typing():
            self.bot.tree.clear_commands(guild=ctx.guild)
            await self.bot.tree.sync(guild=ctx.guild)

        await ctx.reply("Removed guild slash commands from this guild.")

    @sync.command(alias=["global"])
    async def all(self, ctx: GHUtilsContext):
        """Sync global slash commands to all guilds."""

        async with ctx.channel.typing():
            await self.bot.tree.sync()

        await ctx.reply("Synced global slash commands to all guilds.")
