"""Smoke-test extracted release packages; no player or Jellyfin server required."""
import argparse
import configparser
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

ASSETS = ('JellyfinToLocalPlayer.zip', 'JellyfinToLocalPlayer-python-embed-win32.zip')


def check_package(archive, embedded=False):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        package = root / 'application'
        with zipfile.ZipFile(archive) as source:
            source.extractall(package)
        python = str(package / 'python_embed/python.exe') if embedded else sys.executable
        subprocess.run([python, '-c', 'import requests'], cwd=root, check=True)
        config = configparser.ConfigParser()
        config.read(package / 'config.ini', encoding='utf-8-sig')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        config['server']['port'] = str(port)
        config['server']['title'] = 'Release smoke test'
        config['dev'].update(kill_process_at_start='no', use_system_proxy='no', log_file='')
        config_path = root / 'smoke-config.ini'
        with config_path.open('w', encoding='utf-8') as file:
            config.write(file)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        # Launch from outside the package to detect hardcoded relative paths.
        with (root / 'backend.log').open('w+', encoding='utf-8') as log:
            process = subprocess.Popen([python, str(package / 'main.py'), '--config', str(config_path)],
                                       cwd=root, stdout=log, stderr=subprocess.STDOUT)
            try:
                for _ in range(100):
                    if process.poll() is not None:
                        log.seek(0)
                        raise AssertionError(f'Packaged backend exited: {log.read()}')
                    try:
                        with opener.open(f'http://127.0.0.1:{port}/etlp/status', timeout=.5) as response:
                            status = json.load(response)
                        break
                    except OSError:
                        time.sleep(.1)
                else:
                    raise AssertionError('Packaged backend did not become ready')
                assert status['ready'] and status['title'] == 'Release smoke test', status
                for route in ('/embyToLocalPlayer/', '/plexToLocalPlayer/', '/playMediaFile'):
                    try:
                        opener.open(urllib.request.Request(f'http://127.0.0.1:{port}{route}', data=b'{}'), timeout=2)
                    except urllib.error.HTTPError as error:
                        assert error.code == 404, error
                    else:
                        raise AssertionError(f'Removed endpoint accepted: {route}')
            finally:
                process.terminate()
                process.wait(timeout=5)
        print(f'{archive.name}: packaged startup, config, status and removed endpoints passed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifacts', required=True, type=Path)
    parser.add_argument('--run-embedded', action='store_true')
    args = parser.parse_args()
    check_package(args.artifacts / ASSETS[0])
    if args.run_embedded:
        if os.name != 'nt':
            raise RuntimeError('The embedded archive requires Windows')
        check_package(args.artifacts / ASSETS[1], embedded=True)
