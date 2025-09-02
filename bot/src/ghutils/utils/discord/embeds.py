from __future__ import annotations

import re
from typing import overload

from discord import Embed
from githubkit.rest import SimpleUser

from ghutils.utils.markdown import reflow_markdown


def set_embed_author(embed: Embed, user: SimpleUser):
    embed.set_author(
        name=user.login,
        url=user.html_url,
        icon_url=user.avatar_url,
    )
    return embed


_NEWLINE_HEADING_PATTERN = re.compile(r"(\n|^)\n+(#+ +\S)")


@overload
def truncate_markdown_description(text: str, limit: int = ...) -> str: ...


@overload
def truncate_markdown_description(text: str | None, limit: int = ...) -> str | None: ...


def truncate_markdown_description(text: str | None, limit: int = 256) -> str | None:
    if text is None:
        return None

    text = reflow_markdown(text)
    text = _NEWLINE_HEADING_PATTERN.sub(r"\1\2", text)
    text = text.strip()

    if len(text) <= limit:
        return text

    # truncate the string at the first whitespace character after overflowing
    # TODO: would it be better to truncate before instead?
    i = 0
    for c in text:
        if i >= limit and c.isspace():
            break
        i += 1
    return text[:i] + "..."
