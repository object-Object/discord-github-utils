import asyncio

from ghutils.bot.core import GHUtilsBot, GHUtilsEnv
from ghutils.bot.db.models import create_db_and_tables
from ghutils.bot.utils.logging import setup_logging


async def main():
    setup_logging()
    create_db_and_tables()
    env = GHUtilsEnv.get()
    async with GHUtilsBot(env) as bot:
        await bot.load_cogs()
        await bot.start(env.token.get_secret_value())


if __name__ == "__main__":
    asyncio.run(main())
