from typing import Any, Self

from babel.dates import format_date
from discord import ButtonStyle, Interaction, SelectOption
from discord.ui import Button, View, button
from githubkit import GitHub
from githubkit.rest import FullRepository, Release

from ghutils.core.bot import GHUtilsBot
from ghutils.ui.components.paginated_select import (
    MAX_PER_PAGE,
    PaginatedSelect,
    paginated_select,
)
from ghutils.ui.components.visibility import MessageContents, MessageVisibility
from ghutils.ui.embeds.releases import create_release_embed, create_release_items
from ghutils.utils.discord.commands import AnyInteractionCommand
from ghutils.utils.github import ReleaseState, RepositoryName
from ghutils.utils.strings import truncate_str


class GetReleaseView(View):
    bot: GHUtilsBot
    github: GitHub[Any]
    command: AnyInteractionCommand
    repo: FullRepository
    visibility: MessageVisibility

    releases: dict[int, Release]
    release: Release | None

    def __init__(
        self,
        *,
        bot: GHUtilsBot,
        github: GitHub[Any],
        command: AnyInteractionCommand,
        repo: FullRepository,
        visibility: MessageVisibility,
    ):
        """Do not use this constructor directly!"""

        super().__init__(timeout=5 * 60)

        self.bot = bot
        self.github = github
        self.command = command
        self.repo = repo
        self.visibility = visibility

        self.releases = {}
        self.release = None

    async def async_init(self, interaction: Interaction) -> Self:
        await self.release_select.fetch_first_page(interaction)
        return self

    @classmethod
    async def new(
        cls,
        interaction: Interaction,
        repo: FullRepository,
        visibility: MessageVisibility,
    ) -> Self:
        async with GHUtilsBot.github_app_of(interaction) as (github, _):
            return await cls(
                bot=GHUtilsBot.of(interaction),
                github=github,
                command=interaction.command,
                repo=repo,
                visibility=visibility,
            ).async_init(interaction)

    @paginated_select(placeholder="Select a release")
    async def release_select(
        self,
        interaction: Interaction,
        select: PaginatedSelect[Any],
    ):
        assert select.selected_option
        self.release = self.releases[int(select.selected_option.value)]
        self.confirm_button.disabled = False
        await interaction.response.edit_message(view=self)

    @release_select.page_getter()
    async def release_select_page_getter(
        self,
        interaction: Interaction,
        select: PaginatedSelect[Any],
        page: int,
    ) -> list[SelectOption]:
        response = await self.github.rest.repos.async_list_releases(
            owner=self.repo.owner.login,
            repo=self.repo.name,
            per_page=MAX_PER_PAGE,
            page=page,
        )
        select.set_last_page(page, response)

        options = list[SelectOption]()
        for release in response.parsed_data:
            self.releases[release.id] = release

            date = release.published_at or release.created_at

            if release.draft:
                release_type = " (draft)"
            elif release.prerelease:
                release_type = " (pre-release)"
            else:
                release_type = ""

            options.append(
                SelectOption(
                    label=truncate_str(release.name or release.tag_name, 100),
                    value=str(release.id),
                    description=format_date(date, format="long") + release_type,
                )
            )
        return options

    @button(
        label="Confirm",
        style=ButtonStyle.green,
        disabled=True,
    )
    async def confirm_button(self, interaction: Interaction, button: Button[Any]):
        assert self.release

        repo = RepositoryName.from_repo(self.repo)
        state = await ReleaseState.of(self.github, repo, self.release)
        contents = MessageContents(
            command=self.command,
            content=None,
            embed=create_release_embed(repo, self.release, state),
            items=create_release_items(self.release),
        )

        if self.visibility == "private":
            await contents.edit_message(interaction, "private")
        else:
            await interaction.response.edit_message()
            await interaction.delete_original_response()
            await contents.send_followup(interaction, "public", show_usage=True)

        self.stop()
