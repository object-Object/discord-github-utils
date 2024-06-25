import asyncio
import logging

from discord import VoiceClient
from discord.utils import setup_logging

from ghutils_bot.core import EnvSettings, GHUtilsBot


async def main():
    setup_logging()
    VoiceClient.warn_nacl = False
    for name in ["ghutils_bot", "ghutils_common"]:
        logging.getLogger(name).setLevel(logging.DEBUG)

    env = EnvSettings.model_validate({})
    async with GHUtilsBot(env) as bot:
        await bot.load_cogs()
        await bot.start(env.token.get_secret_value())


if __name__ == "__main__":
    asyncio.run(main())
