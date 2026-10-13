# Migrating an existing installation

1. Stop all old backend processes and remove their old `embyToLocalPlayer*.vbs` Startup entries
   (the launcher's option 3 opens that folder). Back up the installation and custom INIs.
2. Extract the new release into a new folder. Use the complete package, including `code/` and `scripts/`.
3. Copy your settings into `config.ini`, or copy your custom instance INIs without changing their filenames.
   Rename the `[emby]` section to `[jellyfin]`. Existing `[emby]` settings are accepted as a compatibility alias
   if `[jellyfin]` is absent, but Emby servers themselves are no longer supported.
4. Keep player executable paths, `[src]`/`[dst]` mappings, ports, titles, `path_check`, playlist/download settings,
   and any subtitle preferences you chose. The new defaults leave subtitle preference/extraction empty;
   an update does not silently clear your own preferences.
5. Remove obsolete `[bangumi]`/`[tg_notify]` settings. `server_data_group` now defaults to Jellyfin;
   a fifth field may be `jellyfin`, but Emby/Plex entries must be removed. The old Emby-only
   `version_filter` and `version_prefer_for_playlist` options are no longer used.
6. Preserve download cache folders and token files if you use them. The old cache index filename is read
   when present. Explicit-instance state is keyed by the absolute config path: moving or renaming a config
   changes its `.instances/` directory and download-cache subdirectory. Copy the old instance's token/state
   files and cache contents into the newly created directories after its first start, with all instances stopped.
7. Replace the whole JavaScript Injector entry using `scripts/jellyfinToLocalPlayer.injector.js`; reapply your
   `SETTINGS.endpoints` and `MOUNT_DISK_ENABLE` choices. Remove the obsolete browser extension/userscript.
   Refresh Jellyfin Web. The backend now accepts `/jellyfinToLocalPlayer/`; the old playback routes are removed.
8. Test using `launch.bat --config your-instance.ini` option 1. Check playback, resume and progress reporting,
   then use option 2 to create the new Startup entry for each instance.

| Old installation path | New path |
| --- | --- |
| `embyToLocalPlayer.py` | `main.py` |
| `embyToLocalPlayer_config.ini` | `config.ini` |
| `utils/` | `code/` |
| `user_script/` | `scripts/` |
| `embyToLocalPlayer_debug.bat` | `launch.bat` |
| `etlp_run.command` | `launch.command` |
| `etlp_run_via_screen.command` | `launch-via-screen.command` |

The default discovery order is `config-<platform>.ini`, then `config.ini` (for example `config-Windows.ini`).
`--config` or the existing `ETLP_CONFIG` environment variable selects an exact file instead.

The old updater downloads old asset names and cannot perform this migration. After migrating, use the new
updater, which targets `k-g-a/JellyfinToLocalPlayer` and the `JellyfinToLocalPlayer.zip` asset. Custom INIs,
logs, tokens, caches, `.instances/` and embedded Python are preserved. Updating changes code for all instances
sharing that installation. Restart them and update the injected JavaScript together.
