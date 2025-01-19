# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Pydantic's HISTORY.md](https://github.com/pydantic/pydantic/blob/main/HISTORY.md), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## `0.2.0` - 2025-01-19

### Added

* GitHub Utils now uses [Fluent](https://projectfluent.org/) to localize command/parameter descriptions.
* Added `/gh user`, by [mercurialworld](https://github.com/mercurialworld) in [#2](https://github.com/object-Object/discord-github-utils/pull/2).

### Changed

* Changed the repository search algorithm to allow fuzzy owner searches (eg. `object/discord` will now suggest `object-Object/discord-github-utils`).
* `/gh_config[_admin] set default_repo` will now return an error if the repository does not exist.
* Added colors to repository and user embeds, by [mercurialworld](https://github.com/mercurialworld) in [#3](https://github.com/object-Object/discord-github-utils/pull/3).

## `0.1.1` - 2024-11-09

### Changed

* Changed the default permissions for `/gh_config_admin` to Manage Server instead of Administrator; the idea is that if a user can add the bot to a server, they should also be able to configure it.

### Fixed

* Added a workaround for the delete button not working in servers or DMs where the bot is not present (ie. user installs).

## `0.1.0` - 2024-11-05

Initial release.
