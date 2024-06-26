import uuid

from discord import Interaction, app_commands
from discord.ext.commands import GroupCog
from discord.ui import Button, View
from github import Github

from ghutils.bot.core import GHUtilsCog


@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
class GitHubCog(GHUtilsCog, GroupCog, group_name="gh"):
    """GitHub-related commands."""

    @app_commands.command()
    async def issue(self, interaction: Interaction):
        """Get a link to a GitHub issue."""

        await interaction.response.defer(ephemeral=False)

    @app_commands.command()
    async def pr(self, interaction: Interaction):
        """Get a link to a GitHub pull request."""

        await interaction.response.defer(ephemeral=False)

    @app_commands.command()
    async def commit(self, interaction: Interaction):
        """Get a link to a GitHub commit."""

        await interaction.response.defer(ephemeral=False)

    @app_commands.command()
    async def login(self, interaction: Interaction):
        """Authorize GitHub Utils to make requests on behalf of your GitHub account."""

        state_id = str(uuid.uuid4())

        gh = Github()

        oauth = gh.get_oauth_application(
            client_id=self.env.github.client_id,
            client_secret=self.env.github.client_secret.get_secret_value(),
        )

        auth_url = oauth.get_login_url(
            redirect_uri=self.env.github.redirect_uri,
            state=state_id,
        )

        await interaction.response.send_message(
            view=View().add_item(Button(label="Login with GitHub", url=auth_url)),
            ephemeral=True,
        )
