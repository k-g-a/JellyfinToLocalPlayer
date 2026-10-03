# Playback and optional features

## Players, progress and episodes

The backend starts a player at Jellyfin's saved position, builds the episode playlist where the adapter
supports it, monitors playback and reports positions when playback stops. Completion is handled through
Jellyfin's playback reporting. `[jellyfin] update_progress = no` disables that final progress update.
`[playlist] enable_host` controls which server names enable playlist handling; `item_limit` limits entries.
MPC-BE can become slow with long playlists; reduce the limit if needed.

The existing player adapters and their limitations remain. mpv/mpv.net offer IPC control, chapter/intro
handling, richer playlist data and retention of subtitle selection between episodes. Existing track settings
are preserved where supported by each adapter. This does not add new cross-player track-selection features.
MPC-HC/MPC-BE normally choose embedded tracks using the player's own preferences; external subtitles can
be passed at launch. IINA's retained integration supports local-file playback. PotPlayer and VLC may disable
HTTP episode playlists when external subtitles cannot be loaded for following episodes; the existing
`[playlist] http_sub_auto_next_ep` option can restart the player near the end to continue playback.

ISO and some live/HLS sources have progress-reporting limitations. Generic executables may launch successfully
without an adapter capable of reporting progress. Close players normally and allow playlist loading to finish.

## Choose a player by path or name

Each button selects its backend instance. That instance first uses `[jellyfin] player`, then applies its own
`[dev] player_by_path` rules. Keys refer to `[exe]` entries; matching is case-insensitive and accepts regular
expressions. Rules are evaluated in order against the server file path and, for STRM, the source path.

```ini
[dev]
player_by_path = be: Dolby Vision, DV; hc: Movies, SDR; vlc: \.iso$, __bdmv;
```

Keep the configured executable paths valid. `__bdmv` is an existing disc-metadata shortcut.
The button's hover title and badge stay attached to the instance, even when a rule chooses another player.

## Subtitles

`[dev] subtitle_priority` and `sub_extract_priority` default to empty, and
`[playlist] http_sub_auto_next_ep` defaults to `no`. There are no default Chinese-language preferences.
Subtitle loading/selection logic itself remains, including Unicode matching, user-selected external
subtitles, optional cross-version extraction, and player-specific handling.

To opt in, supply comma-separated lowercase keywords from subtitle display names, in priority order:

```ini
[dev]
subtitle_priority = english, eng
sub_extract_priority =
```

`sub_extract_priority` allows subtitle extraction from another media version when needed. Leave it empty
to disable that behavior. These values match names; they do not translate subtitles. Player language and
track settings still apply to embedded tracks according to the adapter's capabilities.

## HTTP downloads and persistent cache

These features remain optional and are useful for network playback. They are not needed for mapped local
files. Add a `[gui]` section to your config:

```ini
[gui]
enable = yes
cache_path = D:\JellyfinCache
enable_path =
except_host =
delete_at = 98
cache_size_limit = 100
auto_resume = no
without_confirm = no
```

The prompt offers playback, playback after buffering, head/tail-first download, sequential download,
delete and the download manager. `delete_at` is a completion percentage (100 disables automatic completed
cache removal); `cache_size_limit` is in GB. `enable_path` limits which server paths show the prompt;
`except_host` bypasses it for matching hosts. `without_confirm = yes` starts download-and-play automatically.

The GUI requires Python with Tk support; the embedded runtime's GUI availability depends on its bundled
components. Persistent-cache playlists are limited. If playback catches up with the downloaded data,
close the player to save progress and allow the download to continue. NTFS sparse-file initialization can
be slow; sequential download is an alternative. Explicit configs isolate cache subdirectories.

## Prefetch next episode

The retained prefetch loop warms HTTP caches by reading parts of the next file. It needs a caching proxy or
other upstream cache to benefit later playback; discarded reads alone are not a persistent local download.
Add options to your existing `[playlist]` section:

```ini
[playlist]
prefetch_percent = 50
prefetch_path = /media/series
prefetch_host = jellyfin.example.org
```

`prefetch_percent` is the trigger percentage, `prefetch_path` restricts server paths, and `prefetch_host`
restricts hosts. An empty path filter allows all paths; set the host filter to your Jellyfin host to enable this loop. Advanced existing `prefetch_type` choices are `null`
(discard warming reads), `sequence` and `first_last` (persistent download modes, requiring `[gui]` caching).
The loop depends on playback-time monitoring supplied by the player adapter.

## Prefetch Continue Watching

This independent background worker queries Jellyfin's resume items periodically. Add to `[dev]`:

```ini
[dev]
server_data_group = home, http://localhost:8096, API_KEY, USER_ID;
prefetch_conf = home, /media/series;
```

Each server entry contains name, URL, API key and user ID; separate entries with semicolons. An optional fifth
field may be `jellyfin`. Obtain an API key and the user's ID from your Jellyfin administration settings.
Each `prefetch_conf` entry starts with that server name followed by path prefixes; `/` matches all paths.
The existing STRM metadata warmup is retained. `first_last` as the first value after the server name enables
the persistent head/tail mode for the first resume entries when `[gui]` caching is enabled.

The worker processes the returned resume list; it is not limited to episodes released in the last seven days.
That date filter belonged to the removed Telegram notification path. Both prefetch mechanisms remain
independent of notifications.

## STRM and stream routing

Existing STRM handling is retained, with no new feature development. Normally the player streams through
Jellyfin. `[dev] strm_direct_host` enables direct use of the URL/path inside a STRM for matching Jellyfin
hosts. The player must be able to access that source. Local source paths can use `[src]`/`[dst]` mapping.

Existing optional routing controls:

```ini
[dev]
strm_direct_host =
stream_redirect =
redirect_check_host =
redirect_expire_minute =
stream_prefix =
```

`stream_redirect` contains original/replacement URL pairs separated by commas. `redirect_check_host`
enables resolving and caching redirects for specified domains; `redirect_expire_minute` supplies
`domain:minutes;` expiry rules. These options may help a caching proxy or remote/cloud source; enabling
redirect checks unnecessarily adds startup requests. `stream_prefix` is an advanced URL-prefix facility.

When a STRM has no usable duration, the retained fallback stores positions in memory until restart.
`[dev] server_side_href` can point to another long-running instance for that fallback. The remote instance
requires `[dev] listen_on_localhost = no`; the normal desktop setup should keep its default loopback binding.

## Optional mpv features

mpv is a standalone media player with an IPC API. The existing extras use that API rather than requiring
those features from every player. `[dev] mpv_ipc_playlist_data = yes` sends playlist data to mpv scripts through
`etlp-cmd-pipe`, `etlp-playlist-data` and `etlp-playlist-done` messages.

The existing chapter-based intro/outro helper can be enabled with:

```ini
[dev]
skip_intro = 90, 91, 5, 30, 70, opening, ending, op, ed, hint_only
```

Values describe expected intro/outro lengths, tolerance, percentage bounds and chapter-name matches.
`hint_only` shows a hint; removing it allows automatic skipping. This uses scanned/file chapter data where
available. `[dev] playing_feedback_host` enables the retained experimental real-time mpv progress reporting.
The standalone Lua reporting script is removed; files opened outside this integration are not linked to Jellyfin.

## PotPlayer and Dandan

`[dev] pot_conf` chooses a PotPlayer profile, while `[playlist] mix_s0 = yes` retains explicit playlist loading
in disk mode. Configure PotPlayer's similar-file loading appropriately to avoid competing playlists.
`[dev] media_title_translate` replaces characters in displayed titles, primarily for PotPlayer command-line
compatibility; it must not be used to change file paths.

The Dandan adapter remains optional via `[dandan] enable`, `exe`, `port`, `api_key`, `enable_path` and
`http_seek`. It requires the player's remote-access interface. HTTP seeking can be delayed and external
subtitles are unsupported by that adapter. Normal setup can leave this section absent.

## Trakt and Simkl

Both services remain optional, one-way watched-status reporting. The backend reports completed playback
(over 90%) after the player closes; it does not mirror manual watched toggles from Jellyfin Web.
Existing Jellyfin season metadata helps reconcile watched episodes. Provider IDs such as IMDb, TVDB and
TMDB must be present in the library for matching.

- Create a [Trakt application](https://trakt.tv/oauth/applications) and fill in `[trakt] enable_host`,
  `user_name`, `client_id` and `client_secret`. Use `http://localhost:58000/trakt_auth` as the callback.
- Create a [Simkl application](https://simkl.com/settings/developer/) and fill in `[simkl] enable_host`,
  `client_id` and `client_secret`. Use `http://localhost:58000/simkl_auth` as the callback.

Change the callback port to the instance's `[server] port` when using multiple instances. Start the backend
and complete the authorization page. Tokens live in the instance's runtime directory and survive updates.
Leave `enable_host` empty to disable a provider. Bangumi and Telegram integrations are removed.
