# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Pydantic's HISTORY.md](https://github.com/pydantic/pydantic/blob/main/HISTORY.md), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## `0.1.1`

### Changed

* Changed the default permissions for `/gh_config_admin` to Manage Server instead of Administrator; the idea is that if a user can add the bot to a server, they should also be able to configure it.

### Fixed

* Added a workaround for the delete button not working in servers or DMs where the bot is not present (ie. user installs).

## `0.1.0`

Initial release.
