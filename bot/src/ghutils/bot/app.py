import asyncio
import logging

from discord import VoiceClient
from discord.utils import setup_logging

from ghutils.bot.core import EnvSettings, GHUtilsBot


async def main():
    setup_logging()
    logging.getLogger("ghutils").setLevel(logging.DEBUG)
    VoiceClient.warn_nacl = False

    env = EnvSettings.model_validate({})
    async with GHUtilsBot(env) as bot:
        await bot.load_cogs()
        await bot.start(env.token.get_secret_value())


if __name__ == "__main__":
    asyncio.run(main())
