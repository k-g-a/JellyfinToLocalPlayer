"""Run from the repository root with requests installed: python tests/instances.py."""
import configparser
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

root = Path.cwd()
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]

with tempfile.TemporaryDirectory() as directory:
    directory = Path(directory)
    processes = []
    try:
        for index in range(2):
            config = configparser.ConfigParser()
            config.read(root / 'embyToLocalPlayer_config.ini', encoding='utf-8-sig')
            port = free_port()
            config['server']['port'] = str(port)
            config['server']['title'] = 'madVR' if index == 0 else ''
            config['emby']['player'] = 'hc' if index == 0 else 'be'
            config['dev']['log_file'] = ''
            config['dev']['use_system_proxy'] = 'no'
            config['gui'] = {'cache_path': str(directory / 'cache')}
            path = directory / f'{index}.ini'
            with path.open('w') as file:
                config.write(file)
            result = directory / f'{index}.json'
            code = '''
import json, sys
from utils.configs import configs
from utils.players import get_pipe_or_port_str
from utils.http_server import run_server
from utils.tools import clean_tmp_dir
clean_tmp_dir()
with open(sys.argv[1], 'w') as file:
    json.dump(dict(tmp=configs.tmp_dir, cache=configs.cache_path, runtime=configs.runtime_dir,
                   url=configs.local_server_url, pipe=get_pipe_or_port_str(True),
                   control_port=get_pipe_or_port_str()), file)
run_server()
'''
            process = subprocess.Popen([sys.executable, '-c', code, str(result)],
                env={**os.environ, 'ETLP_CONFIG': str(path)}, stdout=subprocess.DEVNULL)
            processes.append((process, port, result))
        for index, (process, port, result) in enumerate(processes):
            for attempt in range(100):
                assert process.poll() is None, 'Instance exited unexpectedly'
                try:
                    with opener.open(f'http://127.0.0.1:{port}/etlp/status', timeout=.5) as response:
                        status = json.load(response)
                        assert response.headers['Access-Control-Allow-Origin'] == '*'
                    break
                except OSError:
                    time.sleep(.05)
            else:
                raise AssertionError('Instance never became ready')
            assert status['ready'] and status['service'] == 'JellyfinToLocalPlayer'
            assert status['title'] == ('madVR' if index == 0 else 'be')
            assert 'playerProfiles' not in status
            with opener.open(urllib.request.Request(f'http://127.0.0.1:{port}/etlp/status', method='OPTIONS')) as response:
                assert response.status == 204
        records = [json.loads(result.read_text()) for _, _, result in processes]
        for key in ('tmp', 'cache', 'runtime', 'url', 'pipe'):
            assert records[0][key] != records[1][key], key
        # Missing new server section preserves the old port; missing file and bad ports fail.
        legacy = directory / 'legacy.ini'
        config.remove_section('server')
        with legacy.open('w') as file:
            config.write(file)
        check = 'from utils.configs import configs; assert configs.server_port == 58000'
        subprocess.run([sys.executable, '-c', check], env={**os.environ, 'ETLP_CONFIG': str(legacy)}, check=True)
        for value in ('0', '65536', 'invalid'):
            config['server'] = {'port': value}
            with legacy.open('w') as file:
                config.write(file)
            failed = subprocess.run([sys.executable, '-c', check], env={**os.environ, 'ETLP_CONFIG': str(legacy)},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            assert failed.returncode != 0
        print('Instances: concurrent status/CORS, title fallback, isolated state, legacy port and validation passed')
    finally:
        for process, _, _ in processes:
            process.terminate()
        for process, _, _ in processes:
            process.wait(timeout=5)
