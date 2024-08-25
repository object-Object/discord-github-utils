import logging

import discord


def setup_logging():
    discord.utils.setup_logging()
    logging.getLogger("ghutils").setLevel(logging.DEBUG)
    discord.VoiceClient.warn_nacl = False
