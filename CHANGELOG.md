# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Pydantic's HISTORY.md](https://github.com/pydantic/pydantic/blob/main/HISTORY.md), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## `0.5.1` - 2025-09-01

### Changed

* Markdown images are now formatted like `[alt text](link)` instead of `![alt text](link)`.
* Improved Markdown whitespace stripping.
* Increased the Markdown description length limit to 512, and added a maximum line count of 16.

### Fixed

* Fixed multi-line HTML comments not being removed from descriptions.

## `0.5.0` - 2025-09-01

### Added

* Added `/gh release` to get a link to a specific GitHub release, or to open a menu to select one.

### Changed

* Added the [nightly.link](https://nightly.link) icon to the button in `/gh actions artifact`.
* The select menus in `/gh actions artifact` are now paginated.

### Fixed

* Issue/PR descriptions are now parsed as Markdown to remove HTML comments and unnecessary whitespace (fixes [#6](https://github.com/object-Object/discord-github-utils/issues/6)).

## `0.4.1` - 2025-08-31

### Changed

* In `/gh actions artifact`, the update time is now hidden if it's less than one second after the creation time.

## `0.4.0` - 2025-08-31

### Added

* Added `/gh actions artifact` for looking up a specific GitHub Actions artifact.

### Changed

* Updated discord.py to `2.6.2`.

## `0.3.0` - 2025-08-25

### Added

* Added a button to issue/PR/commit messages that updates the embed with the latest details.
  * For example, if you run `/gh issue issue:1`, and then the title of issue #1 is changed, pressing the refresh button will edit the embed title to match the new issue title.
  * This button can only be used once per minute by unauthenticated users (calculated using the message's last edit time).

### Changed

* The "Show GitHub issues" message command now includes the issue description if the message only contains one issue reference.

### Notes

* The previous release should have been `0.3.0` instead of `0.2.4`, since a new feature was added.

## `0.2.4` - 2025-07-14

### Added

* Added a message command to get links to inline issue references.

## `0.2.3` - 2025-05-07

### Changed

* Implemented a system for custom application emoji, currently only used by the "apps icon" when resending a private message publicly.
* Updated discord.py to `2.5.0`.

### Fixed

* Fixed an issue where `/gh search files` would sometimes fail because it took more than 3 seconds to send a response.

## `0.2.2` - 2025-02-17

### Changed

* Several commands now accept a GitHub URL as input (eg. `/gh issue issue:https://github.com/object-Object/discord-github-utils/issues/1`).
* Added the member count to `/gh user` for organizations if the user is logged in, by [mercurialworld](https://github.com/mercurialworld) in [#5](https://github.com/object-Object/discord-github-utils/pull/5).

### Fixed

* `/gh user` no longer fails if the user is an organization, by [mercurialworld](https://github.com/mercurialworld) in [#5](https://github.com/object-Object/discord-github-utils/pull/5).

## `0.2.1` - 2025-02-04

### Changed

* Added user install count to `/gh status`.
* Localized all text in `/gh status`.
* Updated discord.py to `2.5.0a5153+gdb7b2d90`.

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
