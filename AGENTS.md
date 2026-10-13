# JellyfinToLocalPlayer contributor notes

This is a Jellyfin-only Python playback backend plus a JavaScript Injector integration.
Work against `translate`; PRs target `translate`. Release publication is triggered by `fork-release`.

- `main.py`: entry point; `--config` resolves before modules start logging or workers.
- `config.ini`: defaults; `[jellyfin]` selects a player; `[server]` controls one instance/button.
- `code/`: playback, path mapping, player adapters, playlists, progress, downloads, prefetch and reporting.
- `scripts/jellyfinToLocalPlayer.injector.js`: explicit extra Play buttons; preserve native playback.
- `docs/`: setup details, migration, playback capabilities and releases.
- `tests/`: injector tests, live local-instance tests and backend regression tests.

Preserve existing playback behavior, including player-specific track handling, Unicode paths, HTTP/local
playback, subtitles, persistent cache, both prefetch modes, STRM and optional Trakt/Simkl reporting.
Subtitles have empty/off preference defaults. Existing user choices must survive updates.
Do not reintroduce Emby/Plex, qBittorrent, browser userscripts, Bangumi, Telegram or standalone Lua reporting.
`X-Emby-*` HTTP headers are still required by Jellyfin; do not rename these protocol fields.
The old `[emby]` config alias and cache index filename exist only for migration.

`code/__init__.py` is necessary because Python also has a standard-library `code` module.
Standalone helper entry points must insert the project root first on sys.path.
Keep multiple-instance state isolated. Never replace window.fetch/XMLHttpRequest or intercept native Play.
The updater must target this fork, preserve user config/state and reject incompatible release layouts.
See docs/development.md for validation and release commands. Preserve LICENSE and credit to kjtsune.
