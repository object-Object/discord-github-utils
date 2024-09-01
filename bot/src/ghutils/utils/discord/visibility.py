from dataclasses import dataclass
from re import Match
from typing import Any, Literal, Self

from discord import (
    Embed,
    Interaction,
    PartialEmoji,
    ui,
)
from discord.app_commands import Command, ContextMenu
from discord.ui import Button, DynamicItem, Item, View
from discord.utils import MISSING

from .commands import AnyCommand

type MessageVisibility = Literal["public", "private"]


async def respond_with_visibility(
    interaction: Interaction,
    visibility: MessageVisibility,
    *,
    content: Any | None = None,
    embed: Embed = MISSING,
):
    await MessageContents(
        command=interaction.command,
        content=content,
        embed=embed,
    ).send_response(interaction, visibility)


@dataclass(kw_only=True)
class MessageContents:
    command: AnyCommand | ContextMenu | None
    content: Any | None = None
    embed: Embed = MISSING

    async def send_response(
        self,
        interaction: Interaction,
        visibility: MessageVisibility,
        show_user: bool = False,
    ):
        await interaction.response.send_message(
            content=self.content,
            embed=self.embed,
            ephemeral=visibility == "private",
            view=self._get_view(interaction, visibility, show_user),
        )

    def _get_view(
        self,
        interaction: Interaction,
        visibility: MessageVisibility,
        show_user: bool,
    ):
        if visibility == "private":
            return PrivateView(interaction, self)

        view = View(timeout=None).add_item(DeleteButton(interaction.user.id))
        if show_user:
            match self.command:
                case Command(qualified_name=command_name):
                    label = f"{interaction.user.name} used /{command_name}"
                case _:
                    label = f"Sent by {interaction.user.name}"
            view.add_item(
                Button(
                    # FIXME: remove hardcoded emoji id
                    emoji=PartialEmoji(name="apps_icon", id=1279865345250693151),
                    label=label,
                    disabled=True,
                )
            )
        return view


@dataclass
class PrivateView(View):
    original_interaction: Interaction
    message_contents: MessageContents

    def __post_init__(self):
        super().__init__(timeout=None)

    @ui.button(emoji="👁️")
    async def resend_as_public(self, interaction: Interaction, button: Button[Self]):
        await self.original_interaction.delete_original_response()
        await self.message_contents.send_response(interaction, "public", show_user=True)


@dataclass
class DeleteButton(
    DynamicItem[Button[Any]],
    template=r"DeleteButton:user:(?P<id>[0-9]+)",
):
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

    async def interaction_check(self, interaction: Interaction):
        return (
            interaction.user.id == self.user_id
            and interaction.message is not None
            and interaction.message.author == interaction.client.user
        )

    async def callback(self, interaction: Interaction):
        assert interaction.message
        await interaction.message.delete()
