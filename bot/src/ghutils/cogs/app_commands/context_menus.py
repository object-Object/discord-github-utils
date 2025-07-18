import logging
import re
from dataclasses import dataclass
from types import MethodType
from typing import Any, Callable

from discord import Embed, Interaction, Message, app_commands
from discord.abc import MISSING
from discord.app_commands import ContextMenu
from discord.utils import Coro

from ghutils.core.cog import GHUtilsCog
from ghutils.utils.discord.embeds import create_issue_embed
from ghutils.utils.discord.references import IssueReferenceTransformer
from ghutils.utils.discord.visibility import respond_with_visibility

logger = logging.getLogger(__name__)

type ContextMenuCallback[GroupT: GHUtilsCog] = Callable[
    [GroupT, Interaction, Message], Coro[Any]
]

type ContextMenuBuilder[GroupT: GHUtilsCog] = Callable[[GroupT], ContextMenu]


_builders = list[ContextMenuBuilder[Any]]()


def context_menu[GroupT: GHUtilsCog](
    *,
    name: str | app_commands.locale_str,
    nsfw: bool = False,
    auto_locale_strings: bool = True,
    extras: dict[Any, Any] = MISSING,
) -> Callable[[ContextMenuCallback[GroupT]], ContextMenuCallback[GroupT]]:
    def decorator(f: ContextMenuCallback[GroupT]):
        def builder(group: GroupT):
            return ContextMenu(
                name=name,
                callback=MethodType(f, group),
                nsfw=nsfw,
                auto_locale_strings=auto_locale_strings,
                extras=extras,
            )

        _builders.append(builder)
        return f

    return decorator


_issue_pattern = re.compile(
    r"""
    (?<![a-zA-Z`</])
    (?P<value>
        (?P<repo>[\w-]+/[\w-]+)?
        \#
        (?P<reference>[0-9]+)
    )
    (?![a-zA-Z`>])
    """,
    flags=re.VERBOSE,
)


@dataclass(eq=False)
class ContextMenusCog(GHUtilsCog):
    """Context menu commands."""

    def __post_init__(self):
        self._ctx_menus = list[ContextMenu]()

    async def cog_load(self):
        await super().cog_load()

        for builder in _builders:
            ctx_menu = builder(self)
            self._ctx_menus.append(ctx_menu)
            self.bot.tree.add_command(ctx_menu)

    async def cog_unload(self) -> None:
        await super().cog_unload()

        for ctx_menu in self._ctx_menus:
            self.bot.tree.remove_command(ctx_menu.name, type=ctx_menu.type)
        self._ctx_menus.clear()

    @context_menu(name="Show GitHub issues")
    async def show_issues(self, interaction: Interaction, message: Message):
        await interaction.response.defer()

        seen = set[str]()
        embeds = list[Embed]()
        transformer = IssueReferenceTransformer()

        for match in _issue_pattern.finditer(message.content):
            value = match.group("value")
            try:
                repo, issue = await transformer.transform(interaction, value)
            except Exception:
                logger.warning(
                    f"Failed to transform issue reference: {value}", exc_info=True
                )
                continue

            if issue.html_url in seen:
                continue
            seen.add(issue.html_url)

            embeds.append(create_issue_embed(repo, issue, add_body=False))
            if len(embeds) >= 10:
                break

        if not embeds:
            await respond_with_visibility(
                interaction,
                "public",
                content="No issue references found.",
            )
            return

        await respond_with_visibility(
            interaction,
            "public",
            embeds=embeds,
        )
