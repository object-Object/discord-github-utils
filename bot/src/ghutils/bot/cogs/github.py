from __future__ import annotations

import uuid
from enum import Enum, auto

from discord import Interaction, app_commands
from discord.ext.commands import GroupCog
from discord.ui import Button, View
from github import Github

from ghutils.bot.core import GHUtilsCog
from ghutils.bot.db.models import UserGitHubTokens, UserLogin


@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
class GitHubCog(GHUtilsCog, GroupCog, group_name="gh"):
    """GitHub-related commands."""

    @app_commands.command()
    async def issue(self, interaction: Interaction):
        """Get a link to a GitHub issue."""

        github, _ = self._get_github_app(interaction.user.id)
        await interaction.response.send_message(github.get_user().login)

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

        auth_url = self.env.github.get_login_url(state=login.model_dump_json())

        await interaction.response.send_message(
            view=View().add_item(Button(label="Login with GitHub", url=auth_url)),
            ephemeral=True,
        )

    def _get_github_app(self, user_id: int) -> tuple[Github, LoginResult]:
        oauth = self.env.github.get_oauth_application()

        with self.bot.db_session() as session:
            user_tokens = session.get(UserGitHubTokens, user_id)

            if user_tokens is None:
                return self._get_default_installation_app(), LoginResult.LOGGED_OUT

            if user_tokens.is_refresh_expired():
                return self._get_default_installation_app(), LoginResult.EXPIRED

            # authenticate on behalf of the user
            token = user_tokens.get_token(oauth)
            auth = oauth.get_app_user_auth(token)

            # update stored credentials if the current ones expired
            if auth.token != user_tokens.token:
                user_tokens.refresh(auth)
                session.add(user_tokens)
                session.commit()

            return Github(auth=auth), LoginResult.LOGGED_IN

    def _get_default_installation_app(self):
        return Github(auth=self.env.github.get_default_installation_auth())


class LoginResult(Enum):
    LOGGED_IN = auto()
    LOGGED_OUT = auto()
    EXPIRED = auto()
