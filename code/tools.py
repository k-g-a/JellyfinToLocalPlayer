import json
import os.path
import re
import signal
import subprocess
import threading
import time
from typing import Union

import unicodedata

from code.configs import configs, MyLogger

_logger = MyLogger()


def logger_setup(api_key, netloc):
    if not configs.raw.getboolean('dev', 'mix_log', fallback=True):
        MyLogger.need_mix = False
        return
    MyLogger.api_key = api_key
    MyLogger.netloc = netloc
    MyLogger.netloc_replace = MyLogger.mix_host_gen(netloc)


def safe_deleter(file, ext: Union[str, list, tuple] = ('mkv', 'mp4', 'srt', 'ass', 'strm')):
    ext = [ext] if isinstance(ext, str) else ext
    *_, f_ext = os.path.splitext(file)
    if f_ext.replace('.', '') in ext and os.path.exists(file):
        os.remove(file)
        return True


def clean_tmp_dir():
    tmp = configs.tmp_dir
    if os.path.isdir(tmp):
        for file in os.listdir(tmp):
            os.remove(os.path.join(tmp, file))


def scan_cache_dir():
    """:return dict(_id=i.name, path=i.path, stat=i.stat())"""
    return [dict(_id=i.name, path=i.path, stat=i.stat()) for i in os.scandir(configs.cache_path) if i.is_file()]


def load_json_file(file, error_return='list', encoding='utf-8', silence=False):
    try:
        with open(file, encoding=encoding) as f:
            _json = json.load(f)
    except (FileNotFoundError, ValueError):
        silence or _logger.info(f'load json file fail, fallback to {error_return}\n{file}')
        return dict(list=[], dict={})[error_return]
    else:
        return _json


def dump_json_file(obj, file, encoding='utf-8'):
    with open(file, 'w', encoding=encoding) as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def load_dict_jsons_in_folder(directory, required_key=None):
    res = []
    for filename in os.listdir(directory):
        if not filename.lower().endswith('.json'):
            continue

        file_path = os.path.join(directory, filename)
        js = load_json_file(file_path, error_return='dict')
        if required_key and not required_key in js:
            continue
        res.append(js)

    return res


def create_sparse_file(path: str, size: int):
    if os.path.exists(path):
        raise FileExistsError('create_sparse_file: file should not exists')
    if os.name != 'nt':
        with open(path, 'wb') as f:
            f.seek(size - 1)
            f.write(b'\0')
        return

    import ctypes
    from ctypes import wintypes

    with open(path, 'wb') as f:
        pass

    FSCTL_SET_SPARSE = 0x900C4
    GENERIC_WRITE = 0x40000000
    OPEN_EXISTING = 3

    handle = ctypes.windll.kernel32.CreateFileW(
        wintypes.LPCWSTR(path),
        GENERIC_WRITE,
        0,
        None,
        OPEN_EXISTING,
        0,
        None
    )

    if handle == -1 or handle == ctypes.c_void_p(-1).value:
        raise OSError('Failed to open file to set sparse attribute')

    bytes_returned = wintypes.DWORD(0)
    res = ctypes.windll.kernel32.DeviceIoControl(
        handle,
        FSCTL_SET_SPARSE,
        None, 0,
        None, 0,
        ctypes.byref(bytes_returned),
        None
    )

    ctypes.windll.kernel32.CloseHandle(handle)

    if not res:
        raise OSError('Failed to set sparse attribute')

    with open(path, 'r+b') as f:
        f.seek(size - 1)
        f.write(b'\0')


class ThreadWithReturnValue(threading.Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, *, daemon=None):
        threading.Thread.__init__(self, group, target, name, args, kwargs, daemon=daemon)
        self._return = None

    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args, **self._kwargs)

    def join(self):
        threading.Thread.join(self)
        return self._return


def open_local_folder(data):
    path = data['full_path']
    translate_path = translate_path_by_ini(path)
    path = os.path.normpath(translate_path)
    # isdir = os.path.isdir(path)
    isdir = False if os.path.splitext(path)[1] else True
    windows = f'explorer "{path}"' if isdir else f'explorer /select, "{path}"'
    # -R ensures foreground display
    darwin = f'open -R "{path}"'
    linux = f'xdg-open "{path}"' if isdir else f'xdg-open "{os.path.dirname(path)}"'
    cmd = dict(windows=windows, darwin=darwin, linux=linux)[configs.platform.lower()]
    _logger.info(cmd)
    os.system(cmd)


def kill_multi_process(name_re, not_re=None):
    if os.name == 'nt':
        from code.windows_tool import list_pid_and_cmd
        pid_cmd = list_pid_and_cmd(name_re)
    else:
        ps_out = subprocess.Popen(['ps', '-eo', 'pid,command'], stdout=subprocess.PIPE,
                                  encoding='utf-8').stdout.readlines()
        pid_cmd = [i.strip().split(maxsplit=1) for i in ps_out[1:]]
        pid_cmd = [(int(pid), cmd) for (pid, cmd) in pid_cmd if re.search(name_re, cmd)]
    pid_cmd = [(int(pid), cmd) for (pid, cmd) in pid_cmd if not re.search(not_re, cmd)] if not_re else pid_cmd
    my_pids = (os.getpid(), os.getppid())
    killed = False
    for pid, _ in pid_cmd:
        if pid not in my_pids:
            _logger.info('kill', pid, _)
            os.kill(pid, signal.SIGABRT)
            killed = True
    killed and time.sleep(1)


def activate_window_by_pid(pid, sleep=0):
    if os.name != 'nt':
        time.sleep(1.5)
        return

    from code.windows_tool import activate_window_by_win32

    def activate_loop(_sleep=0):
        time.sleep(_sleep)
        for _ in range(100):
            time.sleep(0.5)
            if activate_window_by_win32(pid):
                return

    threading.Thread(target=activate_loop, args=(0,)).start()
    threading.Thread(target=activate_loop, args=(3,)).start()
    time.sleep(sleep)


def force_disk_mode_by_path(file_path):
    ini_str = configs.raw.get('dev', 'force_disk_mode_path', fallback='').replace('，', ',')
    if not ini_str:
        return False
    ini_tuple = tuple(i.strip() for i in ini_str.split(',') if i)
    check = file_path.startswith(ini_tuple)
    _logger.info('disk_mode check', check)
    return check


def use_dandan_exe_by_path(file_path, data=None):
    config = configs.raw
    dandan = config['dandan'] if 'dandan' in config.sections() else {}
    if not dandan or not file_path or not dandan.getboolean('enable'):
        return False
    enable_path = dandan.get('enable_path', '').replace('，', ',')
    enable_path = [i.strip() for i in enable_path.split(',') if i]
    source_path = data.get('source_path')
    _file_path = f'{file_path} | {source_path}' if source_path else file_path
    path_match = [path in _file_path for path in enable_path]
    if any(path_match) or not enable_path:
        return True
    _logger.error(f'dandanplay {enable_path=} \n{path_match=}')


def translate_path_by_ini(file_path, debug=False):
    config = configs.raw
    path_check = config.getboolean('dev', 'path_check', fallback=False)
    if 'src' in config and 'dst' in config and not file_path.startswith('http'):
        src = config['src']
        dst = config['dst']
        # seems to be an ordered dict
        for k, src_prefix in src.items():
            if not file_path.startswith(src_prefix):
                continue
            dst_prefix = dst[k]
            tmp_path = file_path.replace(src_prefix, dst_prefix, 1)
            if not path_check:
                file_path = os.path.abspath(tmp_path)
                break
            nfc_nfd = [unicodedata.normalize('NFC', tmp_path), unicodedata.normalize('NFD', tmp_path)]
            if nfc_nfd[0] == nfc_nfd[1]:
                nfc_nfd = nfc_nfd[:1]
            for _tmp_path in nfc_nfd:
                if os.path.exists(_tmp_path):
                    file_path = os.path.abspath(_tmp_path)
                    break
                else:
                    _logger.info(f'path_check: file not found\n{_tmp_path}')
    return file_path


def select_player_by_path(file_path, data=None):
    confs = configs.raw.get('dev', 'player_by_path', fallback='')
    if not confs:
        return False
    confs = confs.replace('：', ':').replace('，', ',').replace('；', ';')
    confs = [i.strip() for i in confs.split(';') if i]
    data = data or {}
    source_path = data.get('source_path')
    _file_path = f'{file_path} | {source_path}' if source_path else file_path
    for conf in confs:
        player, rule = [i.strip() for i in conf.split(':', maxsplit=1)]
        ru_re = '|'.join([i.strip() for i in rule.split(',') if i])
        if '__bdmv' in ru_re and data and (
                data.get('Container') == 'bluray' or data.get('VideoType') == 'BluRay'):
            _logger.info(f'select {player}, cuz is bdmv')
            return player
        if re.search(ru_re, _file_path, re.I):
            _logger.info(f'select {player}, cuz re {ru_re}')
            return player
    return False


def get_player_cmd(media_path, file_path, data=None):
    # Jellyfin source_path is the content of the strm
    config = configs.raw
    player = config['jellyfin']['player']
    try:
        exe = config['exe'][player]
    except KeyError:
        raise ValueError(f'{player=}, {player} not found, check config ini file') from None
    exe = config['dandan']['exe'] if use_dandan_exe_by_path(file_path, data=data) else exe
    if player_by_path := select_player_by_path(file_path, data=data):
        exe = config['exe'][player_by_path]
    result = [exe, media_path]
    _logger.info('command line:', result)
    if not media_path.startswith('http') and not os.path.exists(media_path):
        raise FileNotFoundError(f'{media_path}\nmay need to disable read disk mode, '
                                f'or enable path_check, see detail in FAQ')
    return result


def version_prefer_jellyfin(sources):
    rules = configs.ini_str_split('dev', 'version_prefer')
    if not rules:
        return sources[0]
    rules = [i.lower() for i in rules]
    name_key = 'Name' if sources[0]['Path'].startswith('http') else 'Path'
    name_list = [os.path.basename(i).lower() for i in [s[name_key] for s in sources]]
    join_str = '_|_'
    name_all = join_str.join(name_list)
    for rule in rules:
        if rule not in name_all:
            continue
        name_all = name_all[:name_all.index(rule)]
        name_list = name_all.split(join_str)
        index = len(name_list) - 1
        _logger.info(f'version_prefer: success with {rule=}')
        return sources[index]
    _logger.info(f'version_prefer: fail\n{name_list}')
    return sources[0]


def main_ep_to_title(main_ep_info):
    # movie
    if 'SeasonId' not in main_ep_info:
        if 'ProductionYear' not in main_ep_info:
            return f"{main_ep_info['Name']}"
        return f"{main_ep_info['Name']} ({main_ep_info['ProductionYear']})"
    # episode
    if 'ParentIndexNumber' not in main_ep_info or 'IndexNumber' not in main_ep_info:
        return f"{main_ep_info['SeriesName']} - {main_ep_info['Name']}"
    if 'IndexNumberEnd' not in main_ep_info:
        return f"{main_ep_info['SeriesName']} S{main_ep_info['ParentIndexNumber']}" \
               f":E{main_ep_info['IndexNumber']} - {main_ep_info['Name']}"
    return f"{main_ep_info['SeriesName']} S{main_ep_info['ParentIndexNumber']}" \
           f":E{main_ep_info['IndexNumber']}-{main_ep_info['IndexNumberEnd']} - {main_ep_info['Name']}"


def main_ep_intro_time(main_ep_info):
    res = {}
    if not main_ep_info.get('Chapters'):
        return res
    chapters = [i for i in main_ep_info['Chapters'][:5] if i.get('MarkerType')
                and not str(i['StartPositionTicks']).endswith('000000000')
                and not (i['StartPositionTicks'] == 0 and i['MarkerType'] == 'Chapter')]
    if not chapters or len(chapters) > 2:
        return res
    for i in chapters:
        if i['MarkerType'] == 'IntroStart':
            res['intro_start'] = i['StartPositionTicks'] // (10 ** 7)
        elif i['MarkerType'] == 'IntroEnd':
            res['intro_end'] = i['StartPositionTicks'] // (10 ** 7)
    return res


def show_version_info(extra_data=None):
    py_script_version = '2026.10.03'
    if not extra_data:
        return py_script_version
    injector_version = extra_data.get('injectorVersion', 'unknown')
    _logger.info(f'PyScript/{py_script_version} Injector/{injector_version}')
    _logger.info(extra_data.get('userAgent'))


def sub_via_other_media_version(media_sources):
    if len(media_sources) == 1:
        return
    sub_match = {}
    for source in media_sources:
        media_streams = source['MediaStreams']
        sub_dict_list = [s for s in media_streams
                         if s['Type'] == 'Subtitle']
        for _sub in sub_dict_list:
            _sub['Order'] = configs.check_str_match(
                f"{str(_sub.get('Title', '') + ',' + _sub['DisplayTitle']).lower()}",
                'dev', 'sub_extract_priority', log=False, order_only=True)
        sub_dict_list = [i for i in sub_dict_list if i['Order'] != 0]
        sub_dict_list.sort(key=lambda s: s['Order'])
        sub_dict = sub_dict_list[0] if sub_dict_list else {}
        if sub_index := sub_dict.get('Index'):
            sub_match[f"{source['Id']}"] = source['Id'], sub_index, sub_dict['Codec']
    return sub_match


def show_confirm_button(message, width, height, result, fallback, timeout=3):
    import tkinter as tk
    res = fallback

    def _main():
        root = tk.Tk()
        root.title('Confirm Button')
        root.attributes('-topmost', True)
        root.bind('<Motion>', lambda i: root.attributes('-topmost', False))
        screenwidth = root.winfo_screenwidth()
        screenheight = root.winfo_screenheight()
        align_str = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
        root.geometry(align_str)
        root.resizable(width=False, height=False)

        def click():
            nonlocal res
            res = result
            root.destroy()

        tk.Button(root, height=height - 5, width=width - 5, text=message, command=click).pack()
        root.after(timeout * 1000, root.destroy)
        root.mainloop()

    _main()
    return res


def debug_beep_win32(skip_debug=False):
    if os.name == 'nt' and (skip_debug or configs.debug_mode):
        import winsound

        winsound.Beep(500, 2000)
