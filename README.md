# JellyfinToLocalPlayer

Play Jellyfin media in a local desktop player, with resume positions and playback progress sent back to Jellyfin.
This project now focuses on **Jellyfin only**, using the server-side **JavaScript Injector** plugin to add external-player buttons to Jellyfin Web.

Playback is the main concern: local path mapping, HTTP playback, episode playlists, progress and watched status,
existing player settings/track handling, subtitles, downloads and prefetching. MPC-HC and MPC-BE are the primary
setup; the existing mpv, mpv.net, PotPlayer, VLC, IINA and Dandan adapters are also retained.

Each running backend instance supplies one extra Play button. Its appearance follows Jellyfin's native button,
with a small `ex` badge (or your configured short title) and a native hover title. The original Play button remains
unchanged. Buttons appear only while their local backend is reachable. No browser extension is needed.

## Start with one player (Windows)

1. Download from [this fork's releases](https://github.com/k-g-a/JellyfinToLocalPlayer/releases):
   - **JellyfinToLocalPlayer-python-embed-win32.zip** includes Python; extract it to a writable folder.
   - **JellyfinToLocalPlayer.zip** uses an installed Python 3.9+; run `python -m pip install -r requirements.txt` after extracting.
2. Open `config.ini`. Set the actual player executable and select its key. For example:

   ```ini
   [exe]
   hc = C:\Program Files\K-Lite Codec Pack\MPC-HC64\mpc-hc64.exe

   [jellyfin]
   player = hc
   update_progress = yes
   fullscreen = yes

   [server]
   port = 58000
   title = MPC-HC / madVR
   short_title = HC
   ```

   Edit these sections in the supplied complete config; the example above is an excerpt.
3. Run **launch.bat**, choose **1** for a console with logs, and leave it running.
4. On your Jellyfin server, install [JavaScript Injector](https://github.com/n00bcodr/Jellyfin-JavaScript-Injector)
   following that project's installation instructions. Create an enabled script entry and paste the full contents of
   [scripts/jellyfinToLocalPlayer.injector.js](scripts/jellyfinToLocalPlayer.injector.js).
5. Refresh Jellyfin Web on the same PC, open a movie or episode and use the additional Play button.
   Default playback streams through Jellyfin. Close the player normally to report progress.

For a stable background run, use `launch.bat` option **2**. It creates a Windows Startup entry and starts the backend.
Option **3** opens the Startup folder. Use option **1** or the following command for debugging:

```bat
python_embed\python.exe main.py
```

With system Python, use `python main.py`. Keep the whole extracted installation together, including `code/`.
For MPC progress tracking, allow its local web interface; the adapter supplies a control port via `/webport`.
Player settings that forbid multiple instances can interfere when running multiple backends using the same player.

On Linux/macOS, install the requirements, choose the appropriate executable in `config.ini`, then run
`python3 main.py` or `bash launch.command`. `launch-via-screen.command` remains available for a background
single-instance run with GNU screen. Player-specific limitations are in [the playback guide](docs/playback.md).

## Read directly from disk or a mounted share

HTTP playback needs no path mapping. For local playback, the client must be able to open the actual file.
Set `MOUNT_DISK_ENABLE = true` near the start of the injector, then map the server's path prefix to the client's:

```ini
[src]
media = /media/movies

[dst]
media = M:\Movies
```

`/media/movies/Film (2020)/Film.mkv` becomes `M:\Movies\Film (2020)\Film.mkv` on Windows.
Prefixes pair by key and are checked in order. Enable `[dev] path_check = yes` to try matching mappings against
existing files and handle Unicode normalization. `launch.bat` option **4** helps derive prefixes.
Use `[dev] force_disk_mode_path` for per-instance path-based overrides when only some media is mounted locally.
After changing injector settings, replace the script entry and refresh Jellyfin Web.

## Multiple instances: N players, N buttons

Copy the **complete** `config.ini` to one file per instance, such as `mpc-hc.ini` and `mpc-be.ini`.
Give each a distinct port and its own player selection:

| Setting | MPC-HC instance | MPC-BE instance |
| --- | --- | --- |
| `[jellyfin] player` | `hc` | `be` |
| `[server] port` | `58000` | `58001` |
| `[server] title` | `MPC-HC / madVR` | `MPC-BE` |
| `[server] short_title` | `HC` | `BE` |

Start each instance separately:

```bat
launch.bat --config mpc-hc.ini
launch.bat --config mpc-be.ini
```

Choose **1** in each launcher for debugging or **2** in each to create separate background startup entries.
You can also run `python_embed\python.exe main.py --config mpc-hc.ini` directly.
`--config` is a launch argument, not an answer to the numeric menu. Use distinct config filenames for startup entries.

The injector checks ports 58000 and 58001 by default. For more instances, edit `SETTINGS` near its top:

```javascript
const SETTINGS = {
    endpoints: [
        'http://127.0.0.1:58000',
        'http://127.0.0.1:58001',
        'http://127.0.0.1:58002',
    ],
};
```

Each reachable endpoint adds its own button. A blank `title` falls back to the configured player key;
blank `short_title` uses `ex`. Short titles accept at most two characters. Missing server settings default to port 58000
and the existing label behavior. Explicit configs keep independent temporary files, relative logs, OAuth tokens,
cache subdirectories and player control endpoints under a config-path identity in `.instances/`.
Use distinct absolute log paths if you override those. Always use `--config` for concurrent instances.

A button selects an instance, whose `[dev] player_by_path` rules can still choose a player by media path/name.
See [playback settings](docs/playback.md). The button title identifies the instance; it does not change per item.

The endpoint is local to the browser's device, not the Jellyfin server. Devices such as WebOS without a running
backend show no external-player button. Browsers may require permission to access local-network endpoints from
a Jellyfin page. If discovery is blocked, check the browser console and the local endpoint
`http://127.0.0.1:58000/etlp/status`.

## Updating and migration

Use `launch.bat` option **6**, or run `python code/update.py` from the installation folder.
The updater downloads this fork's source archive, preserves user INIs and runtime state, and writes
`config-example.ini` plus `config-diff.ini` for review. Stop all instances before updating and restart afterwards.
Refresh the JavaScript Injector entry from `scripts/jellyfinToLocalPlayer.injector.js` as part of each update.
The updater does not replace embedded Python.

**Upgrading from the old layout requires a one-time manual migration.** See [migration instructions](docs/migration.md).
The backend and injector must be upgraded together because the playback endpoint changed.

## Scope and prior work

Most credits go to **[kjtsune](https://github.com/kjtsune)**, the original author of
[embyToLocalPlayer](https://github.com/kjtsune/embyToLocalPlayer). Its playback engine is the basis of this project.
This fork adds English documentation/translation work, Jellyfin 12 compatibility work, JavaScript Injector
integration and multiple independently configured external-player buttons.

Emby, Plex, qBittorrent integration, Bangumi reporting, embyBangumi, embyDouban, embyEverywhere,
Telegram notifications, browser userscripts and the standalone mpv reporting Lua script have been removed.
If you need those features, use the original repository. Trakt/Simkl reporting, downloads/persistent cache,
both prefetch modes and existing STRM handling remain; STRM is maintained without expanding its feature set.
Playback started directly from Explorer is not automatically matched and reported to Jellyfin.

See [advanced playback and reporting](docs/playback.md) and [development and releases](docs/development.md).
