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


_NEWLINE_PATTERN = re.compile(r"\n[ \t]*\n([ \t]*\n)+")

# remove extra newlines before heading, and fix double newline after heading
_NEWLINE_HEADING_PATTERN = re.compile(r"(\n|^)\n+(#+ +[^\n]+(?:\n|$))\n?")


@overload
def truncate_markdown_description(
    text: str,
    limit: int = ...,
    line_limit: int | None = ...,
) -> str: ...


@overload
def truncate_markdown_description(
    text: str | None,
    limit: int = ...,
    line_limit: int | None = ...,
) -> str | None: ...


def truncate_markdown_description(
    text: str | None,
    limit: int = 512,
    line_limit: int | None = 16,
) -> str | None:
    if text is None:
        return None

    text = reflow_markdown(text)
    text = _NEWLINE_PATTERN.sub("\n\n", text)
    text = _NEWLINE_HEADING_PATTERN.sub(r"\1\2", text)
    text = text.strip()

    if len(text) <= limit and line_limit is None:
        return text

    i = 0
    newline_count = 0
    for c in text:
        # truncate the string at the first whitespace character after overflowing
        # TODO: would it be better to truncate before instead?
        if i >= limit and c.isspace():
            break

        if line_limit is not None and c == "\n":
            newline_count += 1
            if newline_count >= line_limit:
                break

        i += 1
    else:
        # if we didn't break or run over the limit, don't truncate
        if i <= limit:
            return text

    return text[:i] + "..."
