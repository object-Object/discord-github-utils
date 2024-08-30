# pyright: reportPrivateUsage=none

from datetime import UTC, datetime

from discord import Color, Embed, Interaction
from discord.app_commands import (
    AppCommandError,
    CommandTree,
    Transformer,
    TransformerError,
)


class GHUtilsCommandTree(CommandTree):
    async def on_error(self, interaction: Interaction, error: AppCommandError):
        if interaction.response.is_done():
            await super().on_error(interaction, error)
            return

        embed = Embed(
            color=Color.red(),
            timestamp=datetime.now(UTC),
        )

        match error:
            case TransformerError(
                value=value,
                type=opt_type,
                transformer=Transformer(_error_display_name=transformer_name),
            ):
                embed.title = "Invalid input!"
                embed.description = f"Failed to convert value from `{opt_type.name}` to `{transformer_name}`."
                embed.add_field(
                    name="Value",
                    value=str(value),
                    inline=False,
                )
            case _:
                await super().on_error(interaction, error)
                embed.title = "Command failed!"
                embed.description = str(error)

        if cause := error.__cause__:
            embed.add_field(
                name="Reason",
                value=str(cause),
                inline=False,
            ).set_footer(
                text=f"{error.__class__.__name__} ({cause.__class__.__name__})",
            )
        else:
            embed.set_footer(
                text=error.__class__.__name__,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)