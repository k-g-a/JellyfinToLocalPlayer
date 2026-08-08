# qbittorrent\_webui\_open_file

Open a folder or play a file in the qBittorrent WebUI.

![](https://github.com/kjtsune/embyToLocalPlayer/raw/main/qbittorrent_webui_open_file/qbittorrent_webui_open_file.png)

**Drawback**

* If a torrent contains multiple files, only the largest one is played.

## Usage

**This script is an add-on to [embyToLocalPlayer](https://github.com/kjtsune/embyToLocalPlayer)
, the tutorial there is generally applicable and sometimes more accurate. Refer to it if you have questions.**


> Basic configuration

1. Download `etlp-python-embed-win32.zip` (**portable version** | Windows only)   
   or `etlp-mpv-py-embed-win32.zip` (includes a portable mpv player | Windows only | see FAQ for shortcuts)  
   or `embyToLocalPlayer.zip` (Windows / Linux / macOS)  
   then extract it to any folder. [Releases page](https://github.com/kjtsune/embyToLocalPlayer/releases)
2. Enter the folder and edit the config file: the player path and player selection in `embyToLocalPlayer_config.ini`. (No configuration needed if using the portable version bundled with mpv.)
3. Install Python (check "add to path") [official site](https://www.python.org/downloads/)
   (No installation needed if using the portable version.)

> **Additional configuration (pay special attention)**

* Add a URL match for this userscript: userscript extension > Installed Scripts > `qbittorrent_webui_open_file` > Edit >
  Settings > User Matches > Add > fill in the qBittorrent WebUI
  URL. [Releases page](https://greasyfork.org/zh-CN/scripts/450015-qbittorrent-webui-open-file)
* Enter the folder and edit the config file: the path translation rules in `embyToLocalPlayer_config.ini`.

> How to run on Windows / macOS / Linux

* Just run it following the original [**embyToLocalPlayer**](https://github.com/kjtsune/embyToLocalPlayer) project instructions

> [Optional] Use network playback (no path translation needed)

* When playing, it first checks whether the file exists on a locally mounted drive. If not, it plays via a LAN http server link.
* The server hosting the file also needs to run embyToLocalPlayer
* External subtitles are not supported.
* Where to fill in: `.ini` > `[dev]`
  ```
    # Whether to listen on the LAN; fill in "no" on the playback client (otherwise it won't work), and "yes" on the server side.
    listen_on_lan = no
  
    # You can fill in a random password, just keep the server and client passwords the same.
    http_server_token = etlp
   
    # The server's listening address; by default it automatically uses the qB WebUI URL, so this can usually be left empty. E.g.: http://192.168.2.111:58000
    server_side_href = 
  ```

