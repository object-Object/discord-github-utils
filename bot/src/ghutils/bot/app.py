import asyncio

from ghutils.bot.core import EnvSettings, GHUtilsBot
from ghutils.bot.utils.logging import setup_logging


async def main():
    setup_logging()
    env = EnvSettings.model_validate({})
    async with GHUtilsBot(env) as bot:
        await bot.load_cogs()
        await bot.start(env.token.get_secret_value())


if __name__ == "__main__":
    asyncio.run(main())
