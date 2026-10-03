"""Update installed code from this fork while preserving configuration and state."""
import os
from pathlib import Path, PurePosixPath
import shutil
import sys
import tempfile
import zipfile
from configparser import ConfigParser

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

RELEASE_URL = ('https://github.com/k-g-a/JellyfinToLocalPlayer/releases/latest/'
               'download/JellyfinToLocalPlayer.zip')
ROOT_FILES = {'main.py', 'launch.bat', 'launch.command', 'launch-via-screen.command',
              'README.md', 'LICENSE', 'requirements.txt'}
CODE_DIRS = {'code', 'scripts', 'docs'}


def check_ini_diff(old_path, new_path, diff_path):
    old_conf = ConfigParser(allow_no_value=True)
    old_conf.read(old_path, encoding='utf-8-sig')
    if not old_conf.has_section('jellyfin') and old_conf.has_section('emby'):
        old_conf['jellyfin'] = dict(old_conf['emby'])
    new_conf = ConfigParser(allow_no_value=True)
    new_conf.read(new_path, encoding='utf-8-sig')
    diff_conf = ConfigParser(allow_no_value=True)
    for section in new_conf.sections():
        old = old_conf[section] if old_conf.has_section(section) else {}
        changes = {key: value for key, value in new_conf[section].items()
                   if key not in old or value != old.get(key)}
        if changes or not old_conf.has_section(section):
            diff_conf[section] = changes
    if diff_conf.sections():
        with open(diff_path, 'w', encoding='utf-8') as file:
            diff_conf.write(file)
        print(f'Configuration differences (review only): {diff_path}')
    else:
        Path(diff_path).unlink(missing_ok=True)


def install_archive(zip_path, destination, config_path):
    """Validate and stage the source archive before replacing application files.

    INIs, tokens, logs, caches, embedded Python and per-instance state are never
    installed from the archive. The new default INI is saved as an example only.
    """
    destination = Path(destination).resolve()
    required = {'main.py', 'config.ini', 'launch.bat', 'code/__init__.py',
                'code/configs.py', 'scripts/jellyfinToLocalPlayer.injector.js'}
    with tempfile.TemporaryDirectory() as temporary, zipfile.ZipFile(zip_path) as archive:
        if not required.issubset(archive.namelist()):
            raise ValueError('Release has an incompatible layout; no files were updated')
        staged = Path(temporary)
        for entry in archive.infolist():
            path = PurePosixPath(entry.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in entry.filename or ':' in entry.filename:
                raise ValueError(f'Unsafe archive path: {entry.filename}')
            if entry.is_dir() or not path.parts:
                continue
            if entry.filename == 'config.ini':
                target = staged / 'config-example.ini'
            elif path.suffix.lower() == '.ini' or '__pycache__' in path.parts or path.suffix == '.pyc':
                continue
            elif entry.filename in ROOT_FILES or path.parts[0] in CODE_DIRS:
                target = staged.joinpath(*path.parts)
            else:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open('wb') as output:
                shutil.copyfileobj(source, output)
        # Do not overwrite an explicitly chosen config, even if it uses a reserved filename.
        protected = Path(config_path).resolve()
        for source in staged.rglob('*'):
            if source.is_file():
                target = destination / source.relative_to(staged)
                if target.resolve() == protected:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        example = staged / 'config-example.ini'
        diff_path = destination / 'config-diff.ini'
        if diff_path.resolve() != protected:
            check_ini_diff(config_path, example, diff_path)
    shutil.rmtree(destination / 'code' / '__pycache__', ignore_errors=True)


def main():
    from code.configs import configs
    from code.net_tools import requests_urllib

    print('Stop all running instances before updating this installation.')
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary) / 'JellyfinToLocalPlayer.zip'
        print(f'Downloading {RELEASE_URL}')
        requests_urllib(RELEASE_URL, save_path=str(archive))
        install_archive(archive, configs.cwd, configs.path)
    print('Updated. Review config-example.ini and config-diff.ini, then restart.')
    print('Replace the script in JavaScript Injector with scripts/jellyfinToLocalPlayer.injector.js.')


if __name__ == '__main__':
    main()
