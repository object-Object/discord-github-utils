import uuid

from discord import Interaction, app_commands
from discord.ext.commands import GroupCog
from discord.ui import Button, View

from ghutils.bot.core import GHUtilsCog
from ghutils.bot.db.models import UserLogin


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

        user_id = interaction.user.id
        login_id = str(uuid.uuid4())

        with self.bot.db_session() as session:
            match session.get(UserLogin, user_id):
                case UserLogin() as login:
                    login.login_id = login_id
                case None:
                    login = UserLogin(user_id=user_id, login_id=login_id)

            session.add(login)
            session.commit()

        oauth = self.env.github.get_oauth_application()
        auth_url = oauth.get_login_url(
            redirect_uri=self.env.github.redirect_uri,
            state=login.model_dump_json(),
        )

        await interaction.response.send_message(
            view=View().add_item(Button(label="Login with GitHub", url=auth_url)),
            ephemeral=True,
        )
