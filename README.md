# discord-github-utils

Discord bot providing useful GitHub-related commands.

## Setup

This project is set up as a monorepo using [Rye](https://rye.astral.sh). To get started, [install Rye](https://rye.astral.sh/guide/installation), then run the following command:

```sh
rye run setup
```

### Discord bot

1. [Create a Discord bot](https://discordpy.readthedocs.io/en/stable/discord.html) for development.
2. Enable the following privileged intents:
   * Message Content: required for the refresh button on the "Show GitHub issues" message command.
3. Copy the bot token.

### GitHub app

1. [Create a GitHub app](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app) for development.
   * Callback URL: `http://localhost:7100/login`
   * Webhook events: No
   * Permissions:
     * Repository:
       * Issues: Read-only
       * Metadata: Read-only
   * Where can this GitHub App be installed: Only on this account
2. Generate and copy a new client secret.
3. Generate and download a new private key.
4. [Install the GitHub app](https://docs.github.com/en/apps/using-github-apps/installing-your-own-github-app) on a repository, eg. your fork of this repo.
5. [Copy the installation ID](https://stackoverflow.com/questions/74462420/where-can-we-find-github-apps-installation-id) (this is the `GITHUB__DEFAULT_INSTALLATION_ID` value, used for making requests on behalf of users who are not logged in).

### Environment variables

`.env`:

```sh
TOKEN="Discord bot token"
GITHUB="{}"
GITHUB__APP_ID="GitHub app id"
GITHUB__CLIENT_ID="GitHub app client id"
GITHUB__CLIENT_SECRET="GitHub app client secret"
GITHUB__REDIRECT_URI="http://localhost:7100/login"
GITHUB__DEFAULT_INSTALLATION_ID="GitHub app repository installation id"

ENVIRONMENT="dev"
API_PORT="7100"
API_ROOT_PATH=""
DB_URL="sqlite:///db.sqlite"
```

`.env.docker`:

```sh
TOKEN="..."
GITHUB__APP_ID="..."
GITHUB__CLIENT_ID="..."
GITHUB__CLIENT_SECRET="..."
GITHUB__REDIRECT_URI="http://localhost:7100/login"
GITHUB__DEFAULT_INSTALLATION_ID="..."
```

`secrets/github__private_key`: GitHub app private key file.

## Running

Local: `rye run bot`

Docker: `docker compose up`
