from __future__ import annotations

from typing import Any

import humanize
from discord import Embed
from discord.ui import Button, Item
from githubkit.rest import Release

from ghutils.utils.discord.embeds import set_embed_author, truncate_markdown_description
from ghutils.utils.github import ReleaseState, RepositoryName, get_reactions_by_emoji
from ghutils.utils.strings import truncate_str


def create_release_embed(
    repo: RepositoryName,
    release: Release,
    state: ReleaseState,
    *,
    add_body: bool = True,
):
    embed = Embed(
        title=truncate_str(f"[{state.title}] {release.name or release.tag_name}", 256),
        url=release.html_url,
        timestamp=release.published_at or release.created_at,
        color=state.color,
    ).set_footer(
        text=f"{repo}@{release.tag_name}",
    )

    assets = list[tuple[str, str, str]]()
    for asset in release.assets:
        assets.append((
            f"**{asset.name}**",
            asset.browser_download_url,
            f" ({humanize.naturalsize(asset.size, binary=True)})",
        ))
    if release.zipball_url:
        assets.append(("**Source code** (zip)", release.zipball_url, ""))
    if release.tarball_url:
        assets.append(("**Source code** (tar.gz)", release.tarball_url, ""))
    if assets:
        embed.add_field(
            name="Assets",
            value="\n".join(f"- [{name}]({url}){size}" for name, url, size in assets),
        )

    if release.reactions and release.reactions.total_count > 0:
        embed.add_field(
            name="Reactions",
            value="\u2002".join(
                f"{emoji}{count}"
                for emoji, count in get_reactions_by_emoji(release.reactions).items()
                if count > 0
            ),
            inline=False,
        )

    if release.body and add_body:
        embed.description = truncate_markdown_description(release.body)

    if release.author:
        set_embed_author(embed, release.author)

    return embed


def create_release_items(release: Release) -> list[Item[Any]]:
    if not release.discussion_url:
        return []
    return [Button(label="Join discussion", url=release.discussion_url)]
