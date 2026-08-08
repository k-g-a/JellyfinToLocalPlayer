# AGENTS.md — Project Overview for AI Agents

## What This Project Is

**JellyfinToLocalPlayer** (also known as `embyToLocalPlayer` / ETLP) is a Python backend + browser userscript system that intercepts media playback clicks in Jellyfin, Emby, and Plex web UIs and redirects them to a local media player installed on the user's machine.

The userscript sends play requests to a local HTTP server (port 58000) which resolves the media path and launches the appropriate player.

---

## Project Structure

```
embyToLocalPlayer.py          # Entry point — starts the HTTP server
embyToLocalPlayer_config.ini  # Main configuration (players, paths, features)
utils/                        # Core logic
  configs.py                  # Config parsing, logging setup, shared config object
  http_server.py              # HTTP server handler (receives userscript requests)
  data_parser.py              # Parses Emby/Plex API responses into playback data
  players.py                  # Player launch functions (mpv, VLC, PotPlayer, etc.)
  player_manager.py           # Manages player lifecycle and progress callbacks
  net_tools.py                # HTTP utilities, progress sync to Emby/Plex/Jellyfin
  tools.py                    # Misc utilities (logging, window activation, etc.)
  emby_api.py                 # Emby/Jellyfin REST API client
  emby_api_thin.py            # Lightweight Emby API client
  plex_api.py                 # Plex REST API client
  bangumi_api.py              # Bangumi.tv API client
  bangumi_sync.py             # Sync watch status to Bangumi.tv
  trakt_api.py                # Trakt API client
  trakt_sync.py               # Sync watch status to Trakt
  simkl_api.py                # Simkl API client
  simkl_sync.py               # Sync watch status to Simkl
  conf_helper.py              # Config file GUI helper
  gui.py                      # Download task manager GUI (tkinter)
  downloader.py               # Prefetch/download manager
  windows_tool.py             # Windows-specific utilities
  python_mpv_jsonipc.py       # mpv JSON IPC library (vendored)
  update.py                   # Self-update helper

embyBangumi/                  # Standalone: sync Bangumi scores → Emby CriticRating
embyDouban/                   # Userscript: show Douban/Bangumi ratings in Emby UI
embyEverywhere/               # Userscript: add Emby jump links on external sites
qbittorrent_webui_open_file/  # Userscript: open/play files from qBittorrent WebUI
user_script/                  # Browser userscripts (the client side)
utils/others/                 # Misc shell scripts and Lua hooks
```

---

## Language & Runtime

- **Python 3** — no build step, run directly
- **No test suite** — manual testing only
- Dependencies: `requests` (and optionally others per sub-project)
- Config: INI format (`embyToLocalPlayer_config.ini`), UTF-8 encoded
- Runs on: Windows, macOS, Linux, Android (Termux)

---

## Key Design Details

- HTTP server listens on `localhost:58000` by default; LAN mode is optional
- Player support: mpv, mpv.net, PotPlayer, MPC-HC, MPC-BE, VLC, IINA
- Third-party sync: Bangumi.tv, Trakt, Simkl (all optional, configured via INI)
- Path translation: maps server-side paths to local mount paths via `[src]`/`[dst]` INI sections
- Subtitle priority and version preference are user-configured keyword lists
- Progress is reported back to Emby/Jellyfin/Plex after playback stops

---

## Things to Know

- **Chinese comments/docs have been translated to English** (done 2026-08-08)
- The `sub_priority` config value contains Chinese subtitle track name keywords — these are runtime filter strings, **not** translatable comments
- The `genres = 动画|anim` value is a regex filter — **do not translate**
- The `debug_title = '东离剑游记'` in `embyBangumi.py` is a test value — leave as-is
- Log file path is configured via `log_file` in `[dev]` section; resets at 10 MB
- Multiple INI files are tried in order: `-dev.ini`, `-test.ini`, `_config.ini`

---

## Sub-project Notes

- **embyBangumi**: Standalone script. Reads `embyBangumi_config.ini`. Requires Emby API key + user ID. Uses `dry_run = yes` by default for safety.
- **embyDouban**: Userscript only — no Python backend needed.
- **embyEverywhere**: Userscript only — no Python backend needed.
- **qbittorrent_webui_open_file**: Userscript that reuses the same ETLP Python backend.
