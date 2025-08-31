from typing import Any, Self

import humanize
from discord import ButtonStyle, Interaction, SelectOption
from discord.ui import (
    ActionRow,
    Button,
    Container,
    LayoutView,
    Section,
    Select,
    TextDisplay,
)
from githubkit import GitHub
from githubkit.rest import Artifact, FullRepository, ShortBranch, Workflow, WorkflowRun
from yarl import URL

from ghutils.core.bot import GHUtilsBot
from ghutils.utils.discord.commands import AnyInteractionCommand
from ghutils.utils.discord.components import update_select_menu_default
from ghutils.utils.discord.mentions import relative_timestamp
from ghutils.utils.discord.visibility import add_visibility_buttons
from ghutils.utils.github import gh_request
from ghutils.utils.strings import join_truthy, truncate_str

WORKFLOW_PREFIX = ".github/workflows/"


class ArtifactContainer(Container[Any]):
    description_text = TextDisplay[Any]("")

    button_row = ActionRow[Any]()

    footer_text = TextDisplay[Any]("")

    def set_artifact(
        self,
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


# TODO: add text inputs if there are >25 options
class SelectArtifactView(LayoutView):
    def __init__(
        self,
        *,
        github: GitHub[Any],
        command: AnyInteractionCommand,
        repo: FullRepository,
        workflows: list[Workflow],
        branches: list[ShortBranch],
    ):
        super().__init__(timeout=5 * 60)

        self.github = github
        self.command = command
        self.repo = repo

        self.workflows = {workflow.id: workflow for workflow in workflows}
        self.artifacts: dict[str, Artifact] = {}

        self.workflow: Workflow | None = None
        self.workflow_run: WorkflowRun | None = None
        self.branch: str | None = None
        self.artifact: Artifact | None = None

        self.workflow_select.options = [
            SelectOption(
                label=truncate_str(workflow.name, 100),
                value=str(workflow.id),
                description=truncate_str(
                    workflow.path.removeprefix(WORKFLOW_PREFIX), 100
                ),
            )
            for workflow in workflows
        ]

        self.branch_select.options = [
            SelectOption(label=branch.name) for branch in branches
        ]

        self.clear_items()
        self.add_item(self.workflow_label_text)
        self.add_item(self.workflow_row)
        self.add_item(self.branch_label_text)
        self.add_item(self.branch_row)

    @classmethod
    async def new(cls, interaction: Interaction, repo: FullRepository) -> Self:
        async with GHUtilsBot.github_app_of(interaction) as (github, _):
            workflows_response = await gh_request(
                github.rest.actions.async_list_repo_workflows(
                    owner=repo.owner.login,
                    repo=repo.name,
                    per_page=25,
                )
            )

            branches = await gh_request(
                github.rest.repos.async_list_branches(
                    owner=repo.owner.login,
                    repo=repo.name,
                    per_page=25,
                )
            )

            return cls(
                # this is *probably* fine?
                github=github,
                command=interaction.command,
                repo=repo,
                workflows=workflows_response.workflows,
                branches=branches,
            )

    async def refresh_artifacts(self):
        if self.workflow is None:
            return

        old_artifact_name = self.artifact.name if self.artifact else None
        self.artifact = None
        self.workflow_run = None

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

            artifacts = (
                await github.rest.actions.async_list_workflow_run_artifacts(
                    owner=self.repo.owner.login,
                    repo=self.repo.name,
                    run_id=run.id,
                    per_page=25,
                )
            ).parsed_data.artifacts

            if not artifacts:
                self.set_error("❌ No artifacts found.", URL(run.html_url))
                return

            self.artifacts.clear()
            self.artifact_select.options.clear()

            for artifact in artifacts:
                self.artifacts[artifact.name] = artifact
                self.artifact_select.options.append(
                    SelectOption(
                        label=artifact.name,
                        description=join_truthy(
                            " ",
                            artifact.created_at
                            and "Created " + humanize.naturaltime(artifact.created_at),
                            artifact.expired and "(expired)",
                        ),
                        default=old_artifact_name == artifact.name,
                    )
                )

            self.add_item(self.artifact_label_text)
            self.add_item(self.artifact_select_row)

            if old_artifact_name in self.artifacts:
                self.set_artifact(old_artifact_name)

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

    @workflow_row.select(
        min_values=1,
        max_values=1,
    )
    async def workflow_select(self, interaction: Interaction, select: Select[Any]):
        workflow_id = int(update_select_menu_default(select, True).value)

        if self.workflow is None or self.workflow.id != workflow_id:
            self.workflow = self.workflows[workflow_id]
            await self.refresh_artifacts()
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.defer()

    # branch

    branch_label_text = TextDisplay[Any]("**Branch** (optional)")

    branch_row = ActionRow[Any]()

    @branch_row.select(
        min_values=0,
        max_values=1,
    )
    async def branch_select(self, interaction: Interaction, select: Select[Any]):
        selected = update_select_menu_default(select)
        branch = selected.value if selected else None

        if self.branch != branch:
            self.branch = branch
            await self.refresh_artifacts()
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.defer()

    # artifact

    artifact_label_text = TextDisplay[Any]("**Artifact**")

    artifact_select_row = ActionRow[Any]()

    @artifact_select_row.select(
        min_values=1,
        max_values=1,
    )
    async def artifact_select(self, interaction: Interaction, select: Select[Any]):
        artifact_name = update_select_menu_default(select, True).value

        if self.set_artifact(artifact_name):
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.defer()

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
