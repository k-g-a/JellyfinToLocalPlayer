import os
import re
import sys
import threading


# Resolve before importing modules: logging and worker processes read this too.
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Run a local JellyfinToLocalPlayer instance')
    parser.add_argument('--config', help='INI file for this instance (defaults to config.ini)')
    args = parser.parse_args()
    if args.config:
        os.environ['ETLP_CONFIG'] = os.path.abspath(args.config)


try:
    sys.path.insert(0, os.path.dirname(__file__))
except Exception:
    pass

from code.downloader import prefetch_resume_tv
from code.http_server import run_server
from code.tools import (configs, MyLogger, kill_multi_process, clean_tmp_dir)
from code.net_tools import check_redirect_cache_expired_loop

if __name__ == '__main__':
    os.chdir(configs.cwd)
    configs.print_version()
    if not configs.explicit_config and configs.raw.getboolean('dev', 'kill_process_at_start', fallback=True):
        kill_multi_process(name_re=f'({re.escape(os.path.abspath(__file__))}|autohotkey_tool|' +
                                   r'mpv.*exe|mpc-.*exe|vlc.exe|PotPlayer.*exe|' +
                                   r'/IINA|/VLC|/mpv)',
                           not_re='(tmux|greasyfork|github)')

    for _provider in 'trakt', 'simkl':
        if configs.raw.get(_provider, 'enable_host', fallback=''):
            from code.trakt_sync import trakt_sync_main
            from code.simkl_sync import simkl_sync_main

            threading.Thread(target={'trakt': trakt_sync_main,
                                     'simkl': simkl_sync_main}[_provider],
                             kwargs={'test': True}, daemon=True).start()

    logger = MyLogger()
    logger.info(__file__)
    clean_tmp_dir()
    configs.necessary_setting_when_server_start()
    threading.Thread(target=prefetch_resume_tv, daemon=True).start()
    threading.Thread(target=check_redirect_cache_expired_loop, daemon=True).start()
    run_server()  # main logic entry point: code.http_server.py
