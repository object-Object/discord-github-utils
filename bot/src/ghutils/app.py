import asyncio

from ghutils.core.bot import GHUtilsBot
from ghutils.core.env import GHUtilsEnv
from ghutils.db.models import create_db_and_tables
from ghutils.utils.logging import setup_logging


async def main():
    setup_logging()
    env = GHUtilsEnv.get()
    async with GHUtilsBot(env) as bot:
        create_db_and_tables(bot.engine)
        await bot.load_translator()
        await bot.load_cogs()
        await bot.start(env.token.get_secret_value())


if __name__ == "__main__":
    # catch KeyboardInterrupt to hide the long unnecessary traceback
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
