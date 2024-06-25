import asyncio

import discord
from discord.utils import setup_logging

from ghutils_bot.core import GHUtilsBot, GHUtilsEnv


async def main():
    setup_logging()
    discord.VoiceClient.warn_nacl = False

    env = GHUtilsEnv.model_validate({})
    async with GHUtilsBot(env) as bot:
        await bot.load_cogs()
        # await bot.start(env.token.get_secret_value())


if __name__ == "__main__":
    asyncio.run(main())
