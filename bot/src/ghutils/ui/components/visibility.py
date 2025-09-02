from dataclasses import dataclass, field
from re import Match
from typing import Any, Awaitable, Callable, Literal, Sequence, overload

from discord import Embed, Interaction
from discord.app_commands import Command
from discord.ui import Button, DynamicItem, Item, LayoutView, View
from discord.utils import MISSING

from ghutils.core.bot import GHUtilsBot
from ghutils.core.types import CustomEmoji
from ghutils.utils.discord.commands import AnyInteractionCommand
from ghutils.utils.discord.components import AnyComponentParent

type MessageVisibility = Literal["public", "private"]


@dataclass(kw_only=True)
class MessageContents:
    command: AnyInteractionCommand
    content: Any | None = MISSING
    embed: Embed = MISSING
    embeds: Sequence[Embed] = MISSING
    items: list[Item[Any]] = field(default_factory=lambda: list())

    async def send(
        self,
        interaction: Interaction,
        visibility: MessageVisibility,
    ):
        if interaction.response.is_done():
            await self.send_followup(interaction, visibility)
        else:
            await self.send_response(interaction, visibility)

    async def send_response(
        self,
        interaction: Interaction,
        visibility: MessageVisibility,
        show_usage: bool = False,
    ):
        await interaction.response.send_message(
            content=self.content,
            embed=self.embed,
            embeds=self.embeds,
            ephemeral=visibility == "private",
            view=self._get_view(interaction, visibility, show_usage),
        )

    async def send_followup(
        self,
        interaction: Interaction,
        visibility: MessageVisibility,
        show_usage: bool = False,
    ):
        await interaction.followup.send(
            content=self.content or MISSING,
            embed=self.embed or MISSING,
            embeds=self.embeds or MISSING,
            ephemeral=visibility == "private",
            view=self._get_view(interaction, visibility, show_usage),
        )

    async def edit_message(
        self,
        interaction: Interaction,
        visibility: MessageVisibility,
        show_usage: bool = False,
    ):
        await interaction.response.edit_message(
            content=self.content,
            embed=self.embed,
            embeds=self.embeds,
            view=self._get_view(interaction, visibility, show_usage),
        )

    async def edit_original_response(
        self,
        interaction: Interaction,
        *,
        view: View | LayoutView | None = MISSING,
    ):
        await interaction.edit_original_response(
            content=self.content,
            embed=self.embed,
            embeds=self.embeds,
            view=view,
        )

    def _get_view(
        self,
        interaction: Interaction,
        visibility: MessageVisibility,
        show_usage: bool,
    ):
        view = View(timeout=None)
        for item in self.items:
            view.add_item(item)
        add_visibility_buttons(
            parent=view,
            interaction=interaction,
            command=self.command,
            visibility=visibility,
            show_usage=show_usage,
            send_as_public=lambda i: self.send_response(i, "public", show_usage=True),
        )
        return view


@dataclass
class SendAsPublicButton(Button[Any]):
    original_interaction: Interaction
    send_as_public: Callable[[Interaction], Awaitable[Any]]

    def __post_init__(self):
        super().__init__(emoji="👁️")

    async def callback(self, interaction: Interaction):
        await self.original_interaction.delete_original_response()
        await self.send_as_public(interaction)


@dataclass
class DeleteButton(
    DynamicItem[Button[Any]],
    template=r"DeleteButton:user:(?P<id>[0-9]+)",
):
    """A button that deletes its message when pressed by the user who created it."""

    user_id: int

    def __post_init__(self):
        super().__init__(
            Button(
                emoji="🗑️",
                custom_id=f"DeleteButton:user:{self.user_id}",
            )
        )

    @classmethod
    async def from_custom_id(
        cls,
        interaction: Interaction,
        item: Item[Any],
        match: Match[str],
    ):
        return cls(user_id=int(match["id"]))

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return

        # if the bot is in DMs, delete_original_response fails with this error:
        # 404 Not Found (error code: 10015): Unknown Webhook
        # but it works if we first "edit" the message that the component is on
        await interaction.response.edit_message()
        await interaction.delete_original_response()


async def respond_with_visibility(
    interaction: Interaction,
    visibility: MessageVisibility,
    *,
    content: Any | None = None,
    embed: Embed = MISSING,
    embeds: Sequence[Embed] = MISSING,
    items: list[Item[Any]] | None = None,
):
    data = MessageContents(
        command=interaction.command,
        content=content,
        embed=embed,
        embeds=embeds,
        items=items if items is not None else [],
    )
    await data.send(interaction, visibility)


@overload
def add_visibility_buttons(
    parent: AnyComponentParent,
    interaction: Interaction,
    visibility: Literal["public"],
    *,
    command: AnyInteractionCommand,
    show_usage: bool,
) -> None: ...


@overload
def add_visibility_buttons(
    parent: AnyComponentParent,
    interaction: Interaction,
    visibility: Literal["private"],
    *,
    send_as_public: Callable[[Interaction], Awaitable[Any]],
) -> None: ...


@overload
def add_visibility_buttons(
    parent: AnyComponentParent,
    interaction: Interaction,
    visibility: MessageVisibility,
    *,
    command: AnyInteractionCommand,
    show_usage: bool,
    send_as_public: Callable[[Interaction], Awaitable[Any]],
) -> None: ...


def add_visibility_buttons(
    parent: AnyComponentParent,
    interaction: Interaction,
    visibility: MessageVisibility,
    *,
    command: AnyInteractionCommand = None,
    show_usage: bool | None = None,
    send_as_public: Callable[[Interaction], Awaitable[Any]] | None = None,
):
    match visibility:
        case "private":
            assert send_as_public is not None
            parent.add_item(SendAsPublicButton(interaction, send_as_public))
        case "public":
            assert show_usage is not None
            parent.add_item(DeleteButton(user_id=interaction.user.id))
            if show_usage:
                parent.add_item(get_command_usage_button(interaction, command))


def get_command_usage_button(
    interaction: Interaction,
    command: AnyInteractionCommand,
) -> Button[Any]:
    match command:
        case Command(qualified_name=command_name):
            label = f"{interaction.user.name} used /{command_name}"
        case _:
            label = f"Sent by {interaction.user.name}"
    bot = GHUtilsBot.of(interaction)
    return Button(
        emoji=bot.get_custom_emoji(CustomEmoji.apps_icon),
        label=label,
        disabled=True,
    )
