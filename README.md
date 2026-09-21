# etlp - embyToLocalPlayer

etlp - Use Emby/Jellyfin to launch PotPlayer mpv IINA MPC VLC for playback, and report playback progress back (optional). Also supports Plex.

**Features**

* Playback also works from the home page. Just click the original play button. Version priority can be configured (when a video has multiple versions).
* Playlist (continuous playback) is supported, and the next episode keeps the same version.
* One-way watched-status sync is supported for bangumi.tv bgm.tv simkl.tv trakt.tv.
* For users with local mounts: you can jump to the folder corresponding to the path. (The button is above the file path shown on the web page.)
* Unsupported players will usually still work, they just will not report progress back.
* You can play directly from qBittorrent WebUI or jump to the corresponding mounted folder.
  [Companion script](https://greasyfork.org/zh-CN/scripts/450015-qbittorrent-webui-open-file)
* Pseudo-aggregated search. [Companion script](https://github.com/kjtsune/embyToLocalPlayer/tree/main/embyEverywhere)

**The following players support progress reporting**

* If you do not have special requirements, mpv-based players generally provide the best overall experience.
* mpv (keyboard-driven) [Windows](https://sourceforge.net/projects/mpv-player-windows/files/64bit/) . macOS
  just drag it into Applications after extracting [macOS](https://laboratory.stolendata.net/~djinn/mpv_osx/).
  flatpak mpv [Linux](https://flathub.org/apps/io.mpv.Mpv).
* mpv.net (mouse-friendly) [Release page](https://github.com/stax76/mpv.net/releases). Other players based on the mpv core usually work too.
* PotPlayer [Release page](https://potplayer.daum.net/)
  If using http playback, **it may say the address is closed**. The fix is in the FAQ.
* MPC-HC [Release page](https://github.com/clsid2/mpc-hc/releases)
* MPC-BE [Release page](https://sourceforge.net/projects/mpcbe/files/MPC-BE/Release%20builds/)
* VLC [Release page](https://www.videolan.org/vlc/)
* IINA (macOS) [Release page](https://iina.io/)

### Usage

> Basic setup

1. Install one userscript extension, any one is enough:
   [Tampermonkey v3](https://chromewebstore.google.com/detail/dhdgffkkebhmkfjojejmpbldmpobfkfo)
   and enable developer mode. [How to enable it](https://www.tampermonkey.net/faq.php#Q209)
   [Tampermonkey v2](https://chromewebstore.google.com/detail/lcmhijbkigalmkeommnijlpobloojgfn) |
   [Violentmonkey](https://chrome.google.com/webstore/detail/violent-monkey/jinjaccalgkegednnccohejagnlnfdag)
   Known issue: newer Chrome versions may fail to install it.
2. Install the userscript and refresh the Emby page. [Release page](https://greasyfork.org/zh-CN/scripts/448648-embytolocalplayer)
3. Choose one of these three options, download and extract the `.zip` to any English-only path. [Release page](https://github.com/kjtsune/embyToLocalPlayer/releases)
    * Recommended: `etlp-mpv-py-embed-win32.zip` (mpv player | Windows only | see FAQ for shortcuts)
      No config file changes are needed; see the `.bat` usage method below.
    * `etlp-python-embed-win32.zip` (Windows only)
      Edit the config file: set the player path and player selection in `embyToLocalPlayer_config.ini`.
    * `embyToLocalPlayer.zip` (Windows / Linux / macOS)
      Install Python (check add to path) [Official site](https://www.python.org/downloads/)
      Edit the config file: set the player path and player selection in `embyToLocalPlayer_config.ini`.

> Jellyfin JavaScript Injector setup

Jellyfin users can install the script through the server-side
[JavaScript Injector plugin](https://github.com/n00bcodr/Jellyfin-JavaScript-Injector) instead of granting a
general-purpose userscript extension access to browser pages.

1. Install JavaScript Injector on the Jellyfin server.
2. Create an injector entry and paste the complete contents of
   [`user_script/embyToLocalPlayer.injector.js`](user_script/embyToLocalPlayer.injector.js) into it.
3. Enable the entry and refresh Jellyfin Web.
4. Copy the complete `embyToLocalPlayer_config.ini` into two files, for example `madvr.ini` and
   `dolby-vision.ini`. In each copy, select the usual `[emby] player` and configure its `[exe]` path.
   Set these optional entries (add the `[server]` section if missing):

   | Setting | `madvr.ini` | `dolby-vision.ini` | If omitted |
   | --- | --- | --- | --- |
   | `[emby] player` | `hc` | `be` | Keep your existing player selection |
   | `[server] port` | `58000` | `58001` | `58000` |
   | `[server] title` | `MPC-HC / madVR` | `MPC-BE / Dolby Vision` | Value of `[emby] player` |

5. Start each instance in a separate terminal using your existing Python environment:

   ```sh
   python embyToLocalPlayer.py --config madvr.ini
   python embyToLocalPlayer.py --config dolby-vision.ini
   ```

The injector probes both local ports independently and shows **Play in MPC-HC / madVR** and
**Play in MPC-BE / Dolby Vision** beside Jellyfin's own Play button when the corresponding service responds.
An absent service produces no button, including on clients without ETLP. Each click goes directly to that
instance; there is no player-profile parameter. Player selection and existing path-based overrides remain
controlled by each instance's normal configuration.

To change discovery ports, edit the injector's local `SETTINGS` object, for example:

```js
const SETTINGS = { endpoints: ['http://127.0.0.1:59000', 'http://127.0.0.1:59001'] };
```

Omitted settings use ports `58000` and `58001`, a 5-second request timeout, and probe intervals of 5 seconds
for available services and 10 seconds for unavailable services. Optional keys are `requestTimeoutMs`,
`probeIntervalAvailableMs`, and `probeIntervalUnavailableMs`. An empty `endpoints` array disables discovery.
The browser must permit requests from Jellyfin Web to loopback; an unreachable or blocked endpoint stays hidden.

Without `--config`, existing config discovery and port `58000` remain unchanged. A blank or missing
`[server] title` uses the configured player name. Restart an instance after changing its port.
Explicit config files get separate temporary files, relative logs, OAuth token files and download-cache
subdirectories under a config-path identity; runtime files live under `.instances/`.
Absolute log paths should be different for each instance. Explicit-config startup skips broad process killing
and automatic embedded-mpv selection so it does not stop or reconfigure another instance. Use `--config` for
**both** processes. Player control ports are selected from available ports and mpv pipes get unique names;
leave `[dev] mpv_input_ipc_server` unset when running multiple mpv instances. If using Trakt or Simkl, register the corresponding instance port in its OAuth redirect URI.

The injector is self-contained and does not replace `window.fetch`, `XMLHttpRequest`, Jellyfin's Play action,
or browser prototypes. It uses Jellyfin's `ApiClient` only when an ETLP button is pressed.
Disk-read mode is enabled for these actions; configure `[src]` and `[dst]` separately in each INI for path mapping.

> Before you begin

* The webpage flashing briefly means it is automatically dismissing the compatible-stream prompt.
* The player must exit to trigger progress reporting.
* If the log shows `serving at 127.0.0.1:58000`, the service started successfully.
* **If you run into issues, check the relevant FAQ below first. Reports that do not follow the required format will be ignored.**

> Windows

1. Double-click `embyToLocalPlayer_debug.bat`
2. If there is no error, press 1 (do not close the window), then test playback from the webpage. (Just click the original play button.)
3. Press 2 to create a startup item and run it in the background. (Hidden window)

* Troubleshooting:
    * If Pot shows Render Pin failed and cannot play, see the FAQ for the fix.
    * If you want to switch an mpv-included package to another player, you need to delete the `mpv_embed` folder.
    * If double-clicking the `.bat` says Python cannot be found,
      or the player cannot play, please test with the portable package that includes mpv.
    * If auto-start fails, check whether the startup item is disabled: Task Manager > Startup.
      In `.bat`, press 3 to check whether `embyToLocalPlayer.vbs` in the startup folder was deleted by antivirus software.
      If it was deleted, you can create the vbs file yourself, then double-click it to test whether it runs in the background correctly. `.vbs` template:
      ```
      CreateObject("Wscript.Shell").Run """<Python folder>\python.exe"" ""<Script folder>\embyToLocalPlayer.py""" , 0, True
      ```
    * If you have an unsolved issue with bat or vbs, you can try the
      [AutoHotkey auto-start solution](https://github.com/kjtsune/embyToLocalPlayer/issues/14#issuecomment-2430602205).
    * **Read the relevant FAQ below before reporting. Reports that do not follow the required format will be ignored.**

**The FAQ on GitHub is the authoritative version.**
https://github.com/kjtsune/embyToLocalPlayer#faq

> macOS / Linux

<details>
<summary>macOS / Linux</summary>

> macOS

* There is currently no tested environment for macOS, so support cannot be provided.

1. In the folder you just saved, right-click > New Terminal at Folder, run `chmod +x *.command`, then press Enter.
2. Double-click `etlp_run.command`. If there is no error, test playback.
3. Enable auto-start at boot (run without a window):
    1. Option 1: just continue to the next step, but this is probably only suitable for Monterey 12 and older systems.
       Option 2: use Homebrew in Terminal to install screen.
       `brew install screen`
       If you do not have Homebrew installed, install Homebrew first.
       `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"`
    2. Launchpad > Automator > File > New > Application > Run Shell Script >
       drag in `etlp_run.command` (option 1) | `etlp_run_via_screen.command` (option 2) >
       click Run and test playback > File > Save > name it and save it to Applications.
    3. Launchpad > the app you just created > double-click to run it in the background, then test playback again.
    4. System Preferences > Users & Groups > Login Items > add the app you just created.
    5. If Monterey 12.6.6 shows a gear icon in the status bar, replace the file-dragging step with the following content. Be sure to change the cd directory to the folder where you saved it.
       `cd ~/App/embyToLocalPlayer && nohup ./etlp_run.command > run.log 2&>1 &`

> Linux

1. `apt install python3-tk` (if there is no error, you can also skip installing it)
2. Add execute permission to `etlp_run.command`, then open it in Terminal.
3. After playback works normally, add it to startup (run without a window):
    * GUI: Debian_Xfce: Settings > Session and Startup > Application Autostart.
    * For systemd service auto-start, see the reference below. If it fails, use the GUI auto-start method.
    <details>
    <summary>systemd service</summary>

    ```
    [Unit]
    Description=embyToLocalPlayer
    After=graphical-session.target

    [Service]
    ExecStart=/root/etlp/etlp_run.command
    ExecStartPre=/bin/bash -c "until loginctl show-session $(loginctl | grep $USER | awk '{print $1}') -p Type | grep -q -e 'x11\|wayland'; do sleep 1; done; sleep 2"
    TimeoutStartSec=infinity

    [Install]
    WantedBy=graphical-session.target
    ```
    </details>

* A newer mpv version is recommended: flatpak mpv:
    ```
    Flatpak: mpv config directory is ~/.var/app/io.mpv.Mpv/config/mpv
    Flatpak: mpv scripts directory is ~/.var/app/io.mpv.Mpv/config/mpv/scripts
    ```

</details>

### FAQ

<details>
<summary>General FAQ</summary>

> General notes

* The minimum supported Python version is 3.8. The minimum supported Windows version is 10.
* Sometimes the ws connection between the browser and Emby disconnects, creating the false impression that progress reporting failed. Wait a bit or manually refresh the page.
* Some domains, including Plex domains, may be affected by DNS pollution. If playback fails, change your system DNS or use a proxy.
* The feedback group is pinned in the channel. Please read the FAQ first and **report issues as required**. Do not DM unless it contains no sensitive data.
  Small updates will be announced in the channel, though there probably will not be many more. You do not need to follow the channel just to report issues. [https://t.me/embyToLocalPlayer](https://t.me/embyToLocalPlayer)

> How to switch modes

* Click the userscript extension icon in the browser on the Emby page to open a menu where you can switch modes.
* Script on this server: enabled (default); disabled: do not use the script on the current domain.
* Disk-read mode: off > launch the local player but use the server's network link. (Default)
* Disk-read mode: on > launch the local player and convert the server path to a local file path. This requires the file to exist locally or be mounted.
  Fill in the path replacement rules in `.ini`. If the server is local, you do not need to set them. In `.bat`, press 4 for the helper setup tool.
  If errors occur, you can try: `dev` > `path_check = yes`. It checks whether the file exists and converts NFC/NFD. Compatibility is better and logs are clearer. (But it will be a bit slower.)
  If it still does not work, provide the log, config file, and the full paths of the media file on the server and the corresponding file on the client when reporting.
* Persistent cache mode only depends on the config file and does not conflict with userscript settings. You do not need to enable disk-read mode.

> How to update

1. Windows: press 6 in `.bat`
   Linux / macOS: open Terminal in the folder containing `.ini`, then run `python3 utils/update.py`
2. Check the differing fields between the new and old config. `embyToLocalPlayer_diff.ini`

* The userscript sometimes also needs to be updated.

> How to report issues

* **Reports that do not follow the required format will be ignored.**

1. Follow `How to update`, update to the latest version, then test again.
   `Windows users should test with the portable package that includes mpv and state whether it works normally.`
2. Run `debug.bat` and choose 1.
   `On macOS or Linux, run etlp_run.command instead.`
3. Test at least two videos from different movies/shows.
4. Screenshot or copy the log from the `.bat`/`.command` window.
   `After selecting text, press Enter to copy it. The log must include the part from startup to the point where the issue occurs. Or just provide
   log.txt from the folder directly.`
5. Explain what issue you encountered and how to reproduce it.
6. [Optional] Disable fuzzy logging. `.ini` > `[dev]` > `mix_log = no`
7. If launching fails (it still plays in the browser, or clicking Play adds no new log to `.bat`), include a screenshot of what appears after clicking the userscript extension icon on the Emby page.
8. For issues with other userscripts, provide a screenshot after refreshing the page, the full browser console log, and relevant configuration info (if any).

> Subtitle / audio track related

* Subtitle/audio-track selection inside Emby is ineffective.
  External subtitle/audio-track selection works, while embedded subtitles are ignored and selected by the player instead.
  Treating embedded subtitles in the video file as external subtitles will cause the player's language settings to stop working. (External subtitles have highest priority.)
  Normal players can all set language priority order.

> Episode playlist (continuous playback | multi-episode progress reporting) related

* Enabled by default; you can change it in `[playlist]` in the config file.
* It is recommended not to disable it. Most features are tied to playlists, and disabling it will remove some functionality.
* It is best not to quit before playlist addition is finished (usually nothing happens, but still recommended).
* Special note: if you use Play All / Shuffle / Playlist on the Emby/Jellyfin web page, only movie and music video types are supported.

* Windows:

    * mpv:
    * mpv.net:
    * vlc:
    * mpc: be: if the playlist has more than 10 entries, it may stutter; hc does not have this problem.
    * pot: if the log shows `KeyError: 'stream.mkv'`, see the FAQ below.
      pot: if the next episode cannot add external http subtitles, the playlist will be disabled.
      pot: disk-read mode may conflict with title beautification and mixed S0, but it does not affect normal use.

* macOS

    * mpv:
    * iina: only disk-read mode is supported, and it can report progress back
    * vlc: if the next episode cannot add external http subtitles, the playlist will be disabled.

* Linux

    * mpv:
    * vlc: if the next episode cannot add external http subtitles, the playlist will be disabled.

</details>

<details>
<summary>Player-related</summary>

> mpv

<details>
<summary>mpv</summary>

* If you run into problems, test with the portable package that includes mpv.
* If it still does not work, try another video or software decoding (`mpv.conf` should keep only the `log-file` option), then check the mpv log.
  `mpv_embed` > `portable_config` > `mpv_log.txt`
  `mpv.conf` > `log-file = <save path>`
* Recommended danmaku plugins:
  https://github.com/Tony15246/uosc_danmaku
  https://github.com/Kosette/danmaku

> mpv_embed

* `mpv.conf` is a simple config I use personally.
* Compared with the original mpv, only a small number of shortcuts and settings were changed.
* To update the version, click `mpv_embed` > `updater.bat`

> mpv_embed shortcuts

<details>
<summary>mpv_embed shortcuts</summary>

* Chinese docs [https://hooke007.github.io/official_man/mpv.html#id4](https://hooke007.github.io/official_man/mpv.html#id4)
* English docs [https://mpv.io/manual/master/#keyboard-control](https://mpv.io/manual/master/#keyboard-control)
* File location: `mpv_embed` > `portable_config` > `input.conf`

    ```
    ## Chinese docs https://hooke007.github.io/official_man/mpv.html#id4
    ## Chinese docs https://hooke007.github.io/official_man/mpv.html#input-conf
    ## English docs https://mpv.io/manual/master/#keyboard-control
    ## Default keys https://github.com/mpv-player/mpv/blob/master/etc/input.conf

    ## The middle mouse button can click OSD buttons on the interface, showing the playlist, subtitle list, audio track list, etc.


    MBTN_LEFT            ignore                       # <No action> [Left click]
    MBTN_LEFT_DBL        cycle fullscreen             # Toggle fullscreen [Double left click]
    MBTN_RIGHT           cycle pause                  # Toggle pause [Right click]
    MBTN_RIGHT_DBL       quit                         # Close MPV [Double right click]
    WHEEL_UP             add volume  10               # Volume + 10 [Wheel up]
    WHEEL_DOWN           add volume -10               # Volume - 10 [Wheel down]

    MBTN_MID             cycle fullscreen             # Toggle fullscreen [Middle button (press wheel)]
    f                    cycle fullscreen             # Toggle fullscreen
    ENTER                cycle fullscreen             # Toggle fullscreen [Enter]

    LEFT                 seek -5                      # Backward 05 seconds [Left arrow]
    RIGHT                seek  5                      # Forward 05 seconds [Right arrow]
    UP                   seek  40                     # Backward 40 seconds [Up arrow]
    DOWN                 seek -40                     # Forward 40 seconds [Down arrow]
    .                    frame-step                   # Next frame
    ,                    frame-back-step              # Previous frame

    [                    add speed -0.1               # Playback speed - (minimum 0.01)
    ]                    add speed  0.1               # Playback speed + (maximum 100)
    {                    multiply speed 0.5           # Halve playback speed
    }                    multiply speed 2.0           # Double playback speed

    ;                    add chapter -1               # Chapter - (Page Down also works)
    '                    add chapter  1               # Chapter + (Page Up also works)
    q                    quit-watch-later             # Close MPV and save watch-later state (save current file state)
    Q                    quit                         # Close MPV

    z                    add sub-delay -0.1           # Subtitle sync advance 100ms
    Z                    add sub-delay -1             # Subtitle sync advance 1000ms
    x                    add sub-delay +0.1           # Subtitle sync delay 100ms
    X                    add sub-delay +1             # Subtitle sync delay 1000ms

    i                    script-binding stats/display-stats           # Temporarily show stats (while shown, 12340 switches pages; pages 2/4/0 can be scrolled with up/down)
    I                    script-binding stats/display-stats-toggle    # Toggle persistent stats display on/off
    TAB                  script-binding stats/display-stats-toggle    # Toggle persistent stats display on/off
    `                    script-binding console/enable                # Enter console (press Esc to exit)
    DEL                  script-binding osc/visibility                # Toggle built-in OSC visibility
    r                    cycle_values video-rotate 90 180 270 0       # Rotate screen orientation
     ```

</details>


> mpv.net

* Set it to close automatically after playback. Do not load the next file. (This makes it easier to trigger progress reporting; `.ini` has playlist-related options.)
  Right click > Settings > Playback > idle:no, auto-load-folder:no (roughly like this)

</details>

> PotPlayer

<details>
<summary>PotPlayer</summary>

* If it shows `Render Pin failed` and cannot play, or the log shows `KeyError: 'stream.mkv'`
  or `pot stop, stop_sec=None` or `The requested operation requires elevation`, try the following solutions:
  Make the following changes in order. After each change, test playback again. If it still does not work, there may be no solution yet; PRs are welcome.
    1. Reset PotPlayer settings.
    2. Switch Pot to version 20240618.
    3. Switch Pot to the latest version.
    4. Local users should see `General FAQ` > `How to switch modes` and use disk-read mode.
    5. Test with mpv to see whether playback works normally.
       Download link for version 240618.
       [potplayer-1-7-22286.exe (v240618)](https://potplayer.en.uptodown.com/windows/download/1018490678)
       | [Scoop](https://github.com/ScoopInstaller/Extras/blob/108f0c0d42347a1cb9a16d8effdad09a7059c22b/bucket/potplayer.json#L11-L12)
       | [winget](https://github.com/microsoft/winget-pkgs/blob/d7aa02cfe97624c51a005b3c7ac42f05f205aff5/manifests/d/Daum/PotPlayer/240618/Daum.PotPlayer.installer.yaml#L84-L85)
       sha256sum `66d03fc13f4949948890675cf62b839b704b542a34a13a180466f93be20d5bc6`

* Local users may consider [MPC-HC](https://github.com/clsid2/mpc-hc/releases), which includes LAV and also supports madVR, MPCVR, BFRC, etc.
  For network users or users without special needs, mpv-based players generally offer the best overall experience.
* [Optional] Options > Playback > Playback window size: Fullscreen
* Preferences / Language / Miscellaneous > After Playback > Exit after current playback (to trigger progress reporting)
* If using http playback, it may say the address is closed. Seen on Win8 32bit.
  Solution: local users should use disk-read mode, or switch to the portable pot package.
  Security unknown: [PotPlayerPortable-220914.zip](https://www.videohelp.com/download/PotPlayerPortable-220914.zip)
  Launch `PotPlayerPortable.exe` once first, but use `C:\<path_to>\PotPlayerPortable\App\PotPlayer\PotPlayer.exe` for playback
  otherwise it will require running as administrator.
* Disk-read mode may conflict with title beautification and mixed S0, but it does not affect normal use. (There is a solution under FAQ > Hidden features.)

</details>

> Other players

<details>
<summary>Other players</summary>

> MPC：

* WebUI will be enabled automatically. When the system firewall prompts you, you can deny it (it will not affect usage).
* WebUI will be enabled automatically. It is recommended to allow access only from localhost: View > Options > Web Interface:
  check Allow access only from localhost
* When MPC plays http, loading and seeking can be slow, and the total video duration may be inaccurate.
  Also, after you click to close the player, the process may remain in the background.
* No external subtitles when MPC plays http:
  MPC-HC Settings > Playback > Output > Subtitle Renderer > Internal Subtitle Renderer
  MPC-BE Settings > Subtitles > Subtitle Renderer > Internal Subtitle Renderer

> IINA

* If it does not fully exit after playback, it will affect progress reporting and static pipe-name configuration.
  Fix: `Settings` > `General`
  Enable `Quit when all windows are closed`
  Disable `Keep window open after playback ends`
* Playlists are not supported in non-disk-read mode.

</details>
</details>

<details>
<summary>bgm.tv / simkl / trakt.tv watch-record storage</summary>

### bgm.tv / simkl / trakt.tv watch-record storage

> General FAQ

* Clash for Windows users:
    * If the log shows: `SSLEOFError(8, 'EOF occurred in violation of protocol (_ssl.c:1129)'))`
    * Solution: Clash > Settings > System Proxy > Specify Protocol > enable.

* Users of the portable package that includes Python do not need to install dependencies. Other users need to install them: run the following in a command-line terminal. If installation fails, try again with proxy enabled or disabled:
  `python -m pip install requests`
  or:
  `python -m pip install requests -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host=mirrors.aliyun.com`

> bangumi.tv (bgm.tv) one-way sync (mark grid)

* Drawbacks:
    1. Sync is one-way to Bangumi only.
    2. It only syncs what the player has played after the player closes normally (clicking watched on the webpage does not trigger it).
    3. Only regular TV episodes are supported, not movies, theatrical releases, etc.
* Instructions:
    1. Visit and create a token at [https://next.bgm.tv/demo/access-token](https://next.bgm.tv/demo/access-token):
       copy the token into ` access_token = ` under the `[bangumi]` section of the ini config file
    2. In the `[bangumi]` section of the ini config file, fill in `enable_host` and `user_name`.
    3. Start the script, play one anime episode, drag to the end, close the player, and check whether the log shows a successful sync.
* Common issues:
    1. Entries with 8 seasons or more, or more than 300 episodes, are not supported for now. At most 10 sequels are looked up.
    2. If the log shows `Unauthorized`, the token has usually expired or was entered incorrectly. On Windows, the token generation page will open automatically.
  3. Episode air-date matching rule: this is used when regular search fails. In this mode, season and episode numbering are ignored; matching succeeds as long as the Emby and bgm episode air dates differ by no more than two days (inclusive).
  4. Because `bgm.tv` `sequel` does not always mean the next season, season matching can be wrong (though after the handling below, the probability is low).
       Currently, among `sequel` entries, a `sequel` is treated as the start of the next season if it has more than 3 episodes and the first episode number is less than 2.
       Only sequels whose type is TV are kept (`the type is shown in gray text to the right of the title`), while OVA, theatrical, WEB, etc. are skipped.
       Exception: if season 1 is WEB, WEB sequels will not be skipped.
       If the synced episode number is below 12 (so it is not a split-cour broadcast), it will also check whether the season air date in Emby (usually the TMDb date) and the air date on bgm.tv
       differ by more than 15 days, to ensure accuracy.
       For Plex, it checks whether the episode air date and the bgm.tv season air date differ by more than 180 days, to ensure accuracy.
       If there are still other special cases, you can report them.
* Use the command line to mark completed entries in the watching list as watched.
    1. Open a command line in the etlp folder.
    2. Portable-package users run: `./python_embed/python.exe ./utils/bangumi_sync.py mark_played`
    3. Other users run: `python utils/bangumi_sync.py mark_played`

> simkl one-way sync

* Drawbacks:
    1. Sync is one-way to simkl only.
    2. It only syncs what the player has played after the player closes normally (clicking watched on the webpage does not trigger it).
    3. Configuration and usage are both cumbersome.
* Instructions:
    1. [Click here to visit the simkl dev page](https://simkl.com/settings/developer/)：
       create an app, choose any name, set Redirect uri to `http://localhost:58000/simkl_auth`, then save it.
       Created apps can be seen at the bottom of the dev page.
    2. In the `[simkl]` section of the ini config file, fill in `enable_host`, `client_id`, and `client_secret`.
    3. Start the script. The verification page will open automatically. Click the Yes button. After a short wait, the webpage will display `etlp: simkl auth success`.
       `simkl_token.json` will be generated automatically in the etlp directory
    4. Play a video, drag to the end, close the player, and check whether the log shows a successful sync.
* Other issues:
    1. If you want to use Emby's built-in simkl plugin, real-time reporting must be enabled, and that plugin has a global 30-second rate limit. Supporting it is not planned for now.

> trakt.tv one-way sync

* Drawbacks:
    1. Media servers usually already have a Trakt plugin.
    2. Sync is one-way to Trakt only.
    3. It only syncs what the player has played after the player closes normally (clicking watched on the webpage does not trigger it).
    4. Configuration and usage are both cumbersome.
* Instructions:
    1. [Click here to visit the Trakt app management page](https://trakt.tv/oauth/applications)：
       create an app, choose any name, set Redirect uri to `http://localhost:58000/trakt_auth`, then save it.
    2. In the `[trakt]` section of the ini config file, fill in `enable_host`, `user_name`, `client_id`, and `client_secret`.
    3. Start the script. The verification page will open automatically. Or click the `Authorize`
       button on the app details page yourself. After granting consent again, the webpage will display `etlp: trakt auth success`. `trakt_token.json` will be generated automatically in the etlp directory
    4. Play a video, drag to the end, close the player, and check whether the log shows a successful sync.
* Common issues:
    1. If sync fails: for movies, check whether IMDb is missing; for shows, check whether each episode has IMDb or TheTVDB listed underneath.

</details>

<details>
<summary>Other</summary>

### Other:

> Jellyfin-related

* After playback on the home page ends, if you replay the **same file** within 10 seconds, the playback time received by the local player will be incorrect.
  Solutions:
    1. This does not happen if you enter the details page before playing; ~~so it is not my fault~~
    2. Wait 10 seconds before playing again;
    3. Refresh the page manually before playing;
    4. ~~Tell me what request I need to send to fix this~~
* Theme-song functionality is not supported yet, so replaying may fail.

> Plex-related

* Possible DNS pollution. If playback fails, change the system DNS or use a proxy.

> Thanks

* [iwalton3/python-mpv-jsonipc](https://github.com/iwalton3/python-mpv-jsonipc)

</details>

<details>
<summary>Hidden features (generally unnecessary / troublesome to configure / unsupported)</summary>

### Hidden features (unsupported):

<details>
<summary>iso / original disc / bdmv related</summary>

> iso / original disc / bdmv related

* VLC is recommended because it supports menu display and network streams.
* Pot and mpv can also play iso bdmv, but they require disk-read mode, meaning path conversion and local file mounting.
* The path needs to be filled in inside strm, then enable strm direct play and disk-read mode.
* iso does not support progress reporting.
* The config option `player_by_path =  vlc: __bdmv, .iso` can be used so VLC is only used when playing original disc sources.

</details>

<details>
<summary>Local redirect / replace playback URL</summary>

> Local redirect / replace playback URL

* Replace playback URLs locally to reduce network redirects and speed up access.
* For alist strm users, replace the alist service address: this solves the issue where cloud storage does not support 302, causing external playback to be limited by the NAS upload speed.
  In this case, you need to fill in `strm_direct_host` and run alist locally. Be sure to include the port, otherwise it will end up replacing the emby server address.
* For users of prefetch next episode: nginx can reverse-proxy only the video stream. Access the origin site in the browser, and redirect the video stream to the local machine. This reduces nginx configuration complexity and bugs.
* Fill in at: `.ini` > `[dev]`
  ```
  # Separate URLs with commas, and fill them in pairs. Original URL, new URL.
  stream_redirect = http://src.src.com, http://reverse.proxy.com, http://192.168.1.1:5244, http://127.0.0.1:5244
  ```

</details>

<details>
<summary>strm LAN-synced playback progress</summary>

* Problem: because strm files lack duration info, emby does not store playback progress, so playback cannot be resumed.
* Built-in solution: when etlp is running on a single machine, progress is temporarily stored in memory. Progress is lost when the script is closed. (Enabled by default; no configuration needed for this feature.)
* LAN solution: run etlp on the NAS or another server at the same time. During playback, it will query and store playback time on the server's etlp. You need to ensure the server runs long-term.
* Server-side eltp setting location: `.ini` > `[dev]`
  ```
    # Whether to listen only on the local address. This is safer, but it prevents communication with other etlp instances. When running on a server, change it to no.
    listen_on_localhost = no
  ```
* Client-side eltp setting location: `.ini` > `[dev]`
  ```
    # The listening address of the etlp instance running on the server, for example: http://192.168.1.23:58000
    # Fill this in on clients only. The server only needs to stop listening on localhost; the server log will show a prompt.
    server_side_href =
  ```

</details>

<details>
<summary>mpv passes data to lua scripts</summary>

* Use `script-message` to pass some data to mpv so other scripts can use it.
* `'script-message', 'etlp-cmd-pipe', cmd_pipe` : command-line IPC pipe name.
* `'script-message', 'etlp-playlist-data', playlist_data` : emby playlist data.
* `'script-message', 'etlp-playlist-done'` : indicates that the mpv playlist has been fully added.
* Fill in at: `.ini` > `[dev]`
  ```
  # Playlist data is large and is not passed by default. Fill this in if you need to enable it.
  mpv_ipc_playlist_data = yes
  ```

</details>

<details>
<summary>mpv auto-skip intro/outro</summary>

* During playback, check chapter duration and title. If they meet the conditions, automatically skip that chapter or only show a hint.
* Requirements:
    * Emby successfully scanned the intro. (Test: disable the script; when playing in the web page, there is a skip-intro button.)
    * Or the video file itself contains intro/outro chapters. (Accuracy is better if chapter titles are standardized, such as "Opening".)
* Principle: if the video file itself has no chapters, the script automatically adds intro chapters to mpv and checks them during playback.
* Fill in at: `.ini` > `[dev]`
  ```
  # Intro is 90 seconds, outro is 91 seconds, 5 seconds of error are allowed, the intro is within the first 30%, the outro is after 70%, possible chapter names for intro/outro (comma-separated, used for auxiliary matching, case-insensitive)
  # To disable, delete it or comment it out with # in front. mpv chapter-jump shortcuts are ; ' Page Up Page Down
  # If it includes the special value hint_only (removable), hint-only mode is enabled and chapters are not skipped automatically. To skip, use the chapter-jump shortcuts.
  skip_intro = 90, 91, 5, 30, 70, opening, ending, op, ed, hint_only
  ```

</details>

<details>
<summary>mpv bangumi trakt standalone sync script</summary>

> mpv bangumi trakt standalone sync script

* Use case: you do not want to use webpage-triggered playback from this tool, but still want to mark the corresponding bangumi/trakt entries as watched.
* Requirements: mpv player, playing a network video stream, and sync triggers when playback progress exceeds 90%.
* Usage:
    1. Download `etlp-python-embed-win32.zip` and extract it to any folder.
       (If you were already using this script before, switch to the portable package and do not run two copies. Or refer to `FAQ > Watch-record storage services` to install Python and dependencies yourself.)
    2. Move the lua file `the folder you just extracted\utils\others\etlp_sync_bgm_trakt.lua` into mpv's scripts folder.
       For example: `directory containing mpv.exe > portable_config > scripts > etlp_sync_bgm_trakt.lua`
    3. Modify the etlp save directory inside `etlp_sync_bgm_trakt.lua` (the folder path you just extracted)
    4. Refer to `FAQ > Watch-record storage services` above and modify the config file: `embyToLocalPlayer_config.ini`
    5. Refer to `Hidden features > Prefetch continue watching` to set `[dev] > server_data_group`. This is used to obtain `user_id`
    6. Play a video and drag progress past 90%, then check the etlp log: `the folder you just extracted > log.txt`. Or check the mpv log.
* Troubleshooting method: test browser-triggered playback using this project.

</details>

<details>
<summary>Prefetch next episode</summary>

> Prefetch next episode

* Prefetch and discard the beginning and end file data of the next episode to speed up episode switching.
* This needs nginx reverse-proxy cache management, which is somewhat troublesome. (Run nginx on the local machine or NAS to cache and slice the video stream.)
  It reads and discards the first 8% and last 2% of the data. In theory, rclone cache settings could also work, but actual test results were poor.
* You only get caching benefits when the browser accesses the LAN reverse-proxy site, or when used together with Local redirect / replace playback URL.
* Fill in at: `.ini` > `[playlist]`
    ```
    # Trigger prefetch when playback progress exceeds 50%, and prefetch the next episode.
    prefetch_percent = 50

    # Only prefetch when the server path contains the following prefixes, comma-separated. Leave empty or delete to enable for all.
    prefetch_path = /mnt/od/TV, /mnt/gd

    # Keywords of domain names that enable this feature, comma-separated. Leave empty or delete to enable for all.
    prefetch_host =
    ```
* If you use cloud storage and a local hard drive together: [Optional] configure local files to use disk-read mode: `.ini` > dev > force_disk_mode_path
* If you reverse-proxy an https site with a self-signed certificate, you can proxy only the video stream and configure certificate verification to be skipped. `.ini` > dev > skip_certificate_verify
  However, some players also validate certificates, so you need to handle that yourself.

</details>

<details>
<summary>Prefetch continue watching</summary>

> Prefetch continue watching

* Similar to Prefetch next episode. Only handles recently released episodes (within 7 days), making it suitable for following ongoing series.
* Attempts to get media info from strm files to speed up startup.
* [Optional] It is more suitable to configure and run this on a machine that is not turned off.
* Fill in at: `.ini` > `[dev]`
  ```
  # Server information, comma-separated within each entry, with each entry ending in a semicolon. If you need multiple servers, continue writing after the semicolon.
  # api_key: Settings > API Keys. user_id: Settings > Users > [username] > look at the browser URL.
  # The final server type is optional and defaults to emby. Set it to jellyfin for Jellyfin 12+.
  server_data_group = myself, http://localhost:8096, api_key, user_id, jellyfin;
                      others, https://www.abc.org, api_key, user_id, emby;
  # Format: server name from the config above, followed by one or more server-side media path prefixes; multiple servers are also separated by semicolons.
  # Prefetch only when the server path contains the path prefix; use / for all paths
  # strm is a special value used only to scrape media duration information. In this mode, release time and path limits are ignored.
  prefetch_conf = myself, strm, /, /od/another-path-prefix;
  ```
* If nginx caching is needed: fill in the reverse-proxy site URL. If you fill in the origin site URL, you need to configure the video-stream redirection above to point to the reverse-proxy site.
  Note that the playback link and the prefetch link are different. `proxy_cache_key "$arg_MediaSourceId$slice_range";`

</details>

<details>
<summary>Follow-up TG notifications</summary>

> Follow-up TG notifications

* When continue-watching entries are updated, send notifications through a Telegram bot. (Checked every 10 minutes)
* Prerequisite: enable Prefetch continue watching.
* Fill in at the top or bottom of `.ini` (use a standalone config section; do not place it inside another config block)
    ```
    ##################################################################
    ### v v # # # # # # # # Follow-up TG notifications # # # # # # # # # # # v v ###

    [tg_notify]

    # Find @BotFather to create a bot. Copy the token and fill it in.
    bot_token =

    # Open the bot you created, click Start or send any message to it, then start this script. The bot will tell you your chat_id.
    chat_id =

    # After filling in chat_id, restart the script. It will test automatically. If it says the test succeeded, you can disable this item.
    get_chat_id = yes

    # Enable this if you only want notifications and do not need the prefetch service.
    disable_prefetch = no

    # Silent notification time ranges, comma-separated. Example: 0-9 means after 0:00 and before 9:00. Similar to clock-style time ranges.
    silence_time = 0-9, 12-14

    # [Optional] You can specify an API endpoint yourself. Search for "TG Bot API reverse proxy" to solve network connectivity issues.
    base_url = https://api.telegram.org
    ```

</details>

<details>
<summary>Persistent cache</summary>

> Configuration

* Fill in at the top or bottom of `.ini` (use a standalone config section; do not place it inside another config block)

    ```
    ##################################################################
    ### v v # # # # # # # Persistent cache (download while watching) # # # # # # # # v v ###

    [gui]

    # Playlist support is not implemented. Feedback about playlist-related issues is not accepted. It is recommended to disable playlists when using this.
    # Whether to cache files to the local hard drive. A menu will pop up during playback. The userscript does not need disk-read mode enabled.
    enable = no

    # Cache path: NTFS support is not ideal. See the FAQ below for solutions.
    cache_path = D:\cache

    # [Optional] Only show the menu when the server file path contains the specified keywords; otherwise play directly. Separate keywords with commas.
    enable_path =

    # When playback progress exceeds 98%, closing the player will delete the cache. Use 100 to disable.
    delete_at = 98

    # Delete old cache when cache size exceeds 100GB.
    cache_size_limit = 100

    # Whether to automatically resume unfinished download tasks after restart
    auto_resume = no

    # Proxy used for downloading. Leave empty if not needed. http://127.0.0.1:7890
    http_proxy =

    # Domains where gui should be disabled: a comma-separated list of contained strings; playback will follow the userscript setting directly.
    except_host = localhost, 127.0.0.1, 192.168. , 192-168-, example.com:8096
    ```

> Persistent cache (download while watching) FAQ

* If playback progress exceeds download progress, it is recommended to close the player to trigger reporting and save playback progress. (The following was tested on Windows):
  mpv and mpv.net will stop playback for more than ten seconds.
  Pot will stop playback or jump to the end. (Remember to drag it back before closing.)
  MPC will exit the player.
  VLC will stop playback.
* Windows: (Linux ext4 and macOS APFS are fine.)
  Problem: the default NTFS filesystem causes extra disk overhead and long initialization time, while ReFS works normally.
  Solutions:
    1. Use `sequential download` (cache playback is only used after the download finishes; clicking Play will fall back to network playback mode)
    2. Win10 Workstation and Enterprise support ReFS. Format the cache drive or partition as ReFS (this will erase data).
    3. Unverified: upgrade to Workstation edition with a key, or convert using a digital-entitlement tool.
    4. Use a virtual machine or another computer with Workstation edition, then pass through the hard drive and format it as ReFS for Win10 to use (confirmed working on Pro).
       Someone reported that Win8.1 can support it by editing the registry.
* Menu that pops up when clicking Play on the webpage:
    1. Play: use cached playback when cache progress is ahead of the playback start point. Otherwise fall back to network mode.
    2. Play after downloading 1%: wait until both the beginning and end 1% are downloaded before launching the player. Everything else is the same as Play.
    3. Download (head/tail first): download the first and last 1% first, allowing download while watching.
    4. Download (sequential download): cannot download while watching.
    5. Delete current download
    6. Download manager

</details>

<details>
<summary>Dandan Player</summary>

> Configuration

* Fill in at the top or bottom of `.ini` (use a standalone config section; do not place it inside another config block)
    ```
    ##################################################################
    ### v v # # # # # # # # # Dandan Player # # # # # # # # # # # # v v ###

    [dandan]
    # Support for dandanplay anime danmaku player.
    # The player must enable remote access and automatic media-library joining. Also use Settings > File Associations > Repair dandanplay dedicated links.

    # Main switch: no = disable, yes = enable.
    enable = no

    # Player path
    exe = C:\Green\dandanplay-x64\dandanplay.exe

    # Remote access port. For better security, change the remote-access IP to 127.0.0.1.
    port = 80

    # If Web authentication was ever enabled for remote access, fill in the API key here. Leave empty if not set. (Note: this is not the password.)
    api_key =

    # Use Dandan playback only when the server path contains the following paths, comma-separated. Leave empty or delete to use Dandan for all files.
    enable_path = /mnt/od/TV, /mnt/disk1/anime, partial path characters also work, anime

    # When playing via http, whether to control the start time. Requires waiting 15 seconds after playback starts.
    http_seek = yes
    ```

> dandanplay FAQ

* The dandan API service takes about 10 seconds to start, so if playback is too short, progress reporting may fail.
* The player must enable remote access and automatic media-library joining. Also use Settings > File Associations > Repair dandanplay dedicated links.
* If playing via http, the following drawbacks apply:
    1. You need to choose danmaku every time. (The filename is already sent to the player for matching.)
    2. At startup it cannot jump to the Emby start time promptly; you need to wait 15 seconds after playback starts. (This does not matter once you finish each episode.)
    3. External subtitles cannot be loaded.
* Disk-read mode: this solves inconsistent progress when switching playback devices (in disk-read mode, progress is stored by Dandan). Sync strategy:
  when Emby progress is greater than 120 seconds, but Dandan Player progress is less than 30 seconds (and the API has never exceeded 120 seconds since startup),
  Dandan Player progress will be adjusted to match Emby, and you need to wait for the API to start.

</details>

<details>
<summary>In Pot disk-read mode: use Emby as the playlist source / beautify playlist titles</summary>

* Fixes these scenarios:
    1. Pot disk-read mode: when playing anime season 1, it misses S0 episodes interleaved by Emby.
    2. Pot disk-read mode: playlists created in Emby cannot be passed to Pot.
    3. Pot disk-read mode: episode playlist titles are misaligned / missing.
* Choose one of these prerequisites:
    1. Pot Options > Preferences > Create from current settings > rename the config file to `emby` (the script will switch to this config automatically during playback):
       Pot Options > switch configuration in the upper-left to emby > Basic > Open similar files strategy > Open selected file only > OK > Close. (The script adds the playlist only during emby playback.)
    2. Pot Options > Basic > Open similar files strategy > Open selected file only. (Drawback: no playlist when playing from a file manager.)
* Fill in at: `.ini` > `[dev]`
  ```
  # Specify the Pot config profile name at startup. Clear it if not needed.
  # If the specified config profile does not exist, Pot will fall back to the reset default config.
  pot_conf = emby
  ```
* Fill in at: `.ini` > `[playlist]`
  ```
  # Fixes missed season-0 episode playback and misaligned/missing playlist titles in Pot disk-read mode. Playlist loading becomes slower, about 1 episode per second.
  mix_s0 = yes
  ```
* If the first file played is from S0, it will keep playing S0 continuously. (General bug; mpv behaves the same.)

</details>

<details>
<summary>Replace media-title characters (Render Pin failed on newer Pot versions) — enabled by default</summary>

* Problem: spaces or some half-width symbols in the title can prevent pot from launching from the command line, so playback fails.
* Solution: replace half-width single/double quotes with full-width ones, and replace spaces with hyphens. This is the default behavior of the config below.
* Fill in at: `.ini` > `[dev]`
  ```
    # This feature may cause other problems. It is recommended to use it only with pot.
    # Configure carefully. Only single characters are accepted, separated in pairs by full-width commas.
    # Do not include extra spaces or quotation marks. Note that the separator is the full-width comma.
    media_title_translate = '，＇，"，＂， ，-
  ```

</details>

<details>
<summary>Use subtitles from other video versions</summary>

* Example effect: extract embedded subtitles from the 1080p version and use them for the 2160p video that has no subtitles.
* Trigger conditions: the video has multiple versions, the current version has no external subtitles, and the embedded subtitle titles do not contain the characters listed in the config below.
* Solution: during playback, extract subtitles from another version of the video that match the language preference below, and use them for the current version.
* Fill in at: `.ini` > `[dev]`
  ```
  # If the video has multiple versions and subtitle titles do not contain the characters below, extract subtitles from other versions for the current video. Letters in the config below must be lowercase. Options are comma-separated, with earlier ones taking priority.
  sub_extract_priority = 中英特效, 双语特效, 简中特效, 简体特效, 特效, 中上, 中英, 双语, 简, simp, 中, chi
  ```

</details>

</details>
