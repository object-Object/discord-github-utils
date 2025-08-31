from __future__ import annotations

from discord import Embed
from githubkit.rest import SimpleUser


def set_embed_author(embed: Embed, user: SimpleUser):
    embed.set_author(
        name=user.login,
        url=user.html_url,
        icon_url=user.avatar_url,
    )
    return embed
