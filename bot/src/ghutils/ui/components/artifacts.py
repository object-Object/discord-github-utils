from typing import Any

import humanize
from discord.ui import (
    ActionRow,
    Button,
    Container,
    TextDisplay,
)
from githubkit.rest import Artifact, FullRepository, Workflow, WorkflowRun
from yarl import URL

from ghutils.core.bot import GHUtilsBot
from ghutils.core.types import CustomEmoji
from ghutils.utils.discord.mentions import relative_timestamp

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
