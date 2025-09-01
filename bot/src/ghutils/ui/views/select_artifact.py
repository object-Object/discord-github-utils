from typing import Any, Self

import humanize
from discord import ButtonStyle, Interaction, SelectOption
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    Section,
    TextDisplay,
)
from githubkit import GitHub
from githubkit.rest import Artifact, FullRepository, Workflow, WorkflowRun
from yarl import URL

from ghutils.core.bot import GHUtilsBot
from ghutils.core.types import CustomEmoji
from ghutils.ui.components.paginated_select import (
    MAX_PAGE_LENGTH,
    PaginatedSelect,
    paginated_select,
)
from ghutils.ui.components.visibility import add_visibility_buttons
from ghutils.utils.discord.commands import AnyInteractionCommand
from ghutils.utils.discord.mentions import relative_timestamp
from ghutils.utils.github import gh_request
from ghutils.utils.strings import join_truthy, truncate_str

WORKFLOW_PREFIX = ".github/workflows/"


class ArtifactContainer(Container[Any]):
    description_text = TextDisplay[Any]("")

    button_row = ActionRow[Any]()

    footer_text = TextDisplay[Any]("")

    def set_artifact(
        self,
        bot: GHUtilsBot,
        repo: FullRepository,
        branch: str | None,
        workflow: Workflow,
        workflow_run: WorkflowRun,
        artifact: Artifact,
    ):
        if not branch and "pull_request" not in workflow_run.event:
            branch = workflow_run.head_branch

        is_normal = workflow.path.startswith(WORKFLOW_PREFIX)
        stripped_workflow_path = workflow.path.removeprefix(WORKFLOW_PREFIX)
        repo_url = URL("https://github.com") / repo.owner.login / repo.name
        workflow_url = repo_url / "actions/workflows" / stripped_workflow_path

        description = [
            f"## `{artifact.name}.zip`",
            f"**Workflow:** [{workflow.name}]({workflow_url})"
            + (
                f" ([{stripped_workflow_path}]({workflow.html_url}))"
                if is_normal
                else ""
            ),
            f"**Workflow run:** [{workflow_run.display_title}]({workflow_run.html_url})",
        ]
        if artifact.created_at:
            description.append(
                f"**Created:** {relative_timestamp(artifact.created_at)}"
            )
            if (
                artifact.updated_at
                and (artifact.updated_at - artifact.created_at).total_seconds() >= 1
            ):
                description.append(
                    f"**Updated:** {relative_timestamp(artifact.updated_at)}"
                )
        if artifact.expires_at:
            d_s = "d" if artifact.expired else "s"
            description.append(
                f"**Expire{d_s}:** {relative_timestamp(artifact.expires_at)}"
            )
        self.description_text.content = "\n".join(description)

        self.button_row.clear_items()
        self.button_row.add_item(
            Button(
                emoji="⬇️",
                label=f"Download ({humanize.naturalsize(artifact.size_in_bytes, binary=True)})",
                url=str(
                    repo_url
                    / "actions/runs"
                    / str(workflow_run.id)
                    / "artifacts"
                    / str(artifact.id)
                ),
                disabled=artifact.expired,
            )
        )
        if branch and is_normal:
            self.button_row.add_item(
                Button(
                    emoji=bot.get_custom_emoji(CustomEmoji.nightly_link),
                    label="nightly.link",
                    url=str(
                        URL("https://nightly.link")
                        / repo.owner.login
                        / repo.name
                        / "workflows"
                        / stripped_workflow_path
                        / branch
                        / artifact.name
                    ),
                )
            )

        self.footer_text.content = f"-# {repo.owner.login}/{repo.name}"
        if branch:
            self.footer_text.content += f"@{branch}"


class SelectArtifactView(LayoutView):
    bot: GHUtilsBot
    github: GitHub[Any]
    command: AnyInteractionCommand
    repo: FullRepository

    workflows: dict[int, Workflow]
    artifacts: dict[str, Artifact]

    workflow: Workflow | None
    workflow_run: WorkflowRun | None
    branch: str | None
    artifact: Artifact | None
    previous_artifact_name: str | None

    def __init__(
        self,
        *,
        bot: GHUtilsBot,
        github: GitHub[Any],
        command: AnyInteractionCommand,
        repo: FullRepository,
    ):
        """Do not use this constructor directly!"""

        super().__init__(timeout=5 * 60)

        self.bot = bot
        self.github = github
        self.command = command
        self.repo = repo

        self.workflows = {}
        self.artifacts = {}

        self.workflow = None
        self.workflow_run = None
        self.branch = None
        self.artifact = None
        self.previous_artifact_name = None

        self.workflow_row.add_item(self.workflow_select)
        self.branch_row.add_item(self.branch_select)
        self.artifact_select_row.add_item(self.artifact_select)

        self.clear_items()
        self.add_item(self.workflow_label_text)
        self.add_item(self.workflow_row)
        self.add_item(self.branch_label_text)
        self.add_item(self.branch_row)

    async def async_init(self, interaction: Interaction) -> Self:
        await self.workflow_select.fetch_first_page(interaction)
        await self.branch_select.fetch_first_page(interaction)
        return self

    @classmethod
    async def new(cls, interaction: Interaction, repo: FullRepository) -> Self:
        async with GHUtilsBot.github_app_of(interaction) as (github, _):
            return await cls(
                bot=GHUtilsBot.of(interaction),
                github=github,
                command=interaction.command,
                repo=repo,
            ).async_init(interaction)

    async def refresh_artifacts(self, interaction: Interaction):
        if self.workflow is None:
            return

        self.previous_artifact_name = self.artifact.name if self.artifact else None
        self.artifact = None
        self.workflow_run = None
        self.artifact_select.clear_cached_pages()
        self.artifacts.clear()

        self.remove_item(self.artifact_label_text)
        self.remove_item(self.artifact_select_row)
        self.remove_item(self.error_section)
        self.remove_item(self.result_container)
        self.remove_item(self.send_as_public_row)

        async with self.github as github:
            runs = (
                await github.rest.actions.async_list_workflow_runs(
                    owner=self.repo.owner.login,
                    repo=self.repo.name,
                    workflow_id=self.workflow.id,
                    branch=self.branch,
                    status="success",
                    exclude_pull_requests=True,
                    per_page=1,
                )
            ).parsed_data.workflow_runs

            if not runs:
                self.set_error(
                    "❌ No workflow runs found.",
                    URL(self.repo.html_url)
                    / "actions/workflows"
                    / self.workflow.name
                    % {"is": "success"}
                    % ({"branch": self.branch} if self.branch else {}),
                )
                return

            self.workflow_run = run = runs[0]

            await self.artifact_select.fetch_first_page(interaction)
            if not self.artifact_select.options:
                self.set_error("❌ No artifacts found.", URL(run.html_url))
                return

            self.add_item(self.artifact_label_text)
            self.add_item(self.artifact_select_row)

            if self.previous_artifact_name in self.artifacts:
                self.set_artifact(self.previous_artifact_name)

            self.previous_artifact_name = None

    def set_error(self, message: str, url: URL):
        self.error_section.clear_items()
        self.error_section.add_item(message)
        self.error_section.accessory = Button(
            style=ButtonStyle.secondary,
            label="GitHub",
            url=str(url),
        )
        self.add_item(self.error_section)

    def set_artifact(self, artifact_name: str) -> bool:
        if self.artifact is not None and self.artifact.name == artifact_name:
            return False

        if self.artifact is None:
            self.add_item(self.result_container)
            self.add_item(self.send_as_public_row)

        self.artifact = self.artifacts[artifact_name]

        assert self.workflow and self.workflow_run
        self.result_container.set_artifact(
            self.bot,
            self.repo,
            self.branch,
            self.workflow,
            self.workflow_run,
            self.artifact,
        )

        return True

    # workflow

    workflow_label_text = TextDisplay[Any]("**Workflow**")

    workflow_row = ActionRow[Any]()

    @paginated_select(
        min_values=1,
        max_values=1,
    )
    async def workflow_select(
        self,
        interaction: Interaction,
        select: PaginatedSelect[Any],
    ):
        assert select.selected_option
        workflow_id = int(select.selected_option.value)

        if self.workflow is None or self.workflow.id != workflow_id:
            self.workflow = self.workflows[workflow_id]
            await self.refresh_artifacts(interaction)
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.defer()

    @workflow_select.page_getter()
    async def workflow_select_page_getter(
        self,
        interaction: Interaction,
        select: PaginatedSelect[Any],
        page: int,
    ) -> list[SelectOption]:
        workflows = (
            await self.github.rest.actions.async_list_repo_workflows(
                owner=self.repo.owner.login,
                repo=self.repo.name,
                per_page=MAX_PAGE_LENGTH,
                page=page,
            )
        ).parsed_data.workflows

        options = list[SelectOption]()
        for workflow in workflows:
            self.workflows[workflow.id] = workflow
            options.append(
                SelectOption(
                    label=truncate_str(workflow.name, 100),
                    value=str(workflow.id),
                    description=truncate_str(
                        workflow.path.removeprefix(WORKFLOW_PREFIX), 100
                    ),
                )
            )
        return options

    # branch

    branch_label_text = TextDisplay[Any]("**Branch** (optional)")

    branch_row = ActionRow[Any]()

    @paginated_select(
        min_values=0,
        max_values=1,
    )
    async def branch_select(
        self,
        interaction: Interaction,
        select: PaginatedSelect[Any],
    ):
        branch = select.selected_option.value if select.selected_option else None

        if self.branch != branch:
            self.branch = branch
            await self.refresh_artifacts(interaction)
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.defer()

    @branch_select.page_getter()
    async def branch_select_page_getter(
        self,
        interaction: Interaction,
        select: PaginatedSelect[Any],
        page: int,
    ) -> list[SelectOption]:
        branches = await gh_request(
            self.github.rest.repos.async_list_branches(
                owner=self.repo.owner.login,
                repo=self.repo.name,
                per_page=MAX_PAGE_LENGTH,
                page=page,
            )
        )
        return [SelectOption(label=branch.name) for branch in branches]

    # artifact

    artifact_label_text = TextDisplay[Any]("**Artifact**")

    artifact_select_row = ActionRow[Any]()

    @paginated_select(
        min_values=1,
        max_values=1,
    )
    async def artifact_select(
        self,
        interaction: Interaction,
        select: PaginatedSelect[Any],
    ):
        assert select.selected_option
        artifact_name = select.selected_option.value

        if self.set_artifact(artifact_name):
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.defer()

    @artifact_select.page_getter()
    async def artifact_select_page_getter(
        self,
        interaction: Interaction,
        select: PaginatedSelect[Any],
        page: int,
    ) -> list[SelectOption]:
        if not self.workflow_run:
            return []

        artifacts = (
            await self.github.rest.actions.async_list_workflow_run_artifacts(
                owner=self.repo.owner.login,
                repo=self.repo.name,
                run_id=self.workflow_run.id,
                per_page=MAX_PAGE_LENGTH,
                page=page,
            )
        ).parsed_data.artifacts

        if not artifacts:
            return []

        options = list[SelectOption]()
        for artifact in artifacts:
            self.artifacts[artifact.name] = artifact
            options.append(
                SelectOption(
                    label=artifact.name,
                    description=join_truthy(
                        " ",
                        artifact.created_at
                        and "Created " + humanize.naturaltime(artifact.created_at),
                        artifact.expired and "(expired)",
                    ),
                    default=self.previous_artifact_name == artifact.name,
                )
            )
        return options

    # result

    error_section = Section[Any](accessory=Button())

    result_container = ArtifactContainer()

    send_as_public_row = ActionRow[Any]()

    @send_as_public_row.button(emoji="👁️")
    async def send_as_public_button(
        self,
        interaction: Interaction,
        button: Button[Any],
    ):
        self.timeout = None

        self.clear_items()

        self.add_item(self.result_container)

        self.send_as_public_row.clear_items()
        add_visibility_buttons(
            self.send_as_public_row,
            interaction,
            visibility="public",
            command=self.command,
            show_usage=True,
        )
        self.add_item(self.send_as_public_row)

        await interaction.response.edit_message()
        await interaction.delete_original_response()
        await interaction.followup.send(view=self, ephemeral=False)
