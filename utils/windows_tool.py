# ref: https://sjohannes.wordpress.com/tag/win32/

import ctypes
import json
import re
import subprocess
import time

from utils.configs import MyLogger

logger = MyLogger()
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))


def list_pid_and_cmd(name_re: str = '.') -> list:
    cmd = 'Get-WmiObject Win32_Process | Select-Object ProcessId, CommandLine | ConvertTo-Json'
    name_re = re.compile(name_re)
    try:
        proc = subprocess.run(['chcp', '65001', '>', 'NUL', '&', 'powershell', cmd],
                              capture_output=True, encoding='utf-8-sig', shell=True)
    except FileNotFoundError:
        raise FileNotFoundError('powershell not found in cmd, check sys and user environment path') from None
    if proc.returncode != 0:
        return []
    stdout = proc.stdout
    try:
        stdout = json.loads(stdout)
    except Exception:
        logger.error(f'{stdout=}')
        logger.error('powershell stdout error, kill python by yourself in task manager if you need to restart script')
        return []
    result = [(i['ProcessId'], i['CommandLine']) for i in stdout
              if i['ProcessId'] and i['CommandLine'] and name_re.search(i['CommandLine'])]
    return result


class RECT(ctypes.Structure):
    _fields_ = [
        ('left', ctypes.c_long),
        ('top', ctypes.c_long),
        ('right', ctypes.c_long),
        ('bottom', ctypes.c_long),
    ]


def activate_window_by_win32(pid):
    max_size = 0
    max_size_hwnd = None

    def activate_window(hwnd):
        nonlocal max_size
        nonlocal max_size_hwnd
        target_pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(target_pid))
        # Note a process may have multiple windows, need to filter out the most suitable one
        if pid == target_pid.value:
            # Exclude invisible windows
            visible = user32.IsWindowVisible(hwnd)
            if not visible:
                return False
            # Exclude windows with an empty title
            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return False

            # buff = ctypes.create_unicode_buffer(length + 1)
            # user32.GetWindowTextW(hwnd, buff, length + 1)
            # print(f'title: {buff.value}')

            # The above two filters already pass tests for mpv, mpc-be, mpc-hc, vlc and potplayer
            # To be compatible with more other players, keep the largest window among the remaining ones
            rect = RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            # print(f'left: {rect.left}, right: {rect.right}, top: {rect.top}, bottom: {rect.bottom}')
            if (rect.right - rect.left) * (rect.bottom - rect.top) <= max_size:
                return False
            max_size = (rect.right - rect.left) * (rect.bottom - rect.top)
            max_size_hwnd = hwnd
            return True
        else:
            return False

    def each_window(hwnd, _):
        if activate_window(hwnd):
            pass
            # print("Activate: {0}".format(pid))
        return 1

    proc = EnumWindowsProc(each_window)
    user32.EnumWindows(proc, 0)

    if max_size_hwnd is not None:
        # SetForegroundWindow requires at least one of the following conditions to activate a window
        # https://learn.microsoft.com/zh-cn/windows/win32/api/winuser/nf-winuser-setforegroundwindow
        # 1. The calling process is the foreground process.
        # 2. The calling process was launched by the foreground process.
        # 3. There is currently no foreground window, so there's no foreground process.
        # 4. The calling process received the last input event.
        # 5. The foreground process or the calling process is being debugged.

        # Some special operations are needed to achieve this

        # The current thread pid, i.e. the thread of the current python program, is the caller of the player process
        curr_pid = kernel32.GetCurrentThreadId()
        # The currently active window
        foreground_hwnd = user32.GetForegroundWindow()
        # The pid of the currently active window
        remote_pid = user32.GetWindowThreadProcessId(foreground_hwnd, 0)
        # Key point
        # https://learn.microsoft.com/zh-cn/windows/win32/api/winuser/nf-winuser-attachthreadinput
        # Attach one thread's input processing mechanism to another thread, so the two threads share input state
        # This satisfies condition 4: the calling process received the last input event
        user32.AttachThreadInput(curr_pid, remote_pid, True)
        user32.SetForegroundWindow(max_size_hwnd)
        user32.BringWindowToTop(max_size_hwnd)
        # Detach the two threads
        user32.AttachThreadInput(curr_pid, remote_pid, False)
        return True

def process_is_running_by_pid(pid):
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    SYNCHRONIZE = 0x00100000
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, False, pid)
    if handle:
        kernel32.CloseHandle(handle)
        return True
    else:
        return False


def process_is_running_by_pid_window_exist(pid, timeout=5):
    if not process_is_running_by_pid(pid):
        return False
    is_running = False

    def check_pid_exists(hwnd):
        nonlocal is_running
        target_pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(target_pid))
        if pid == target_pid.value:
            is_running = True

    def for_each_window(hwnd, _):
        check_pid_exists(hwnd)
        return True

    start_time = time.time()
    while time.time() - start_time < timeout:
        proc = EnumWindowsProc(for_each_window)
        user32.EnumWindows(proc, 0)
        if is_running:
            return is_running
        time.sleep(0.2)
    return is_running


def find_pid_by_windows_title(title):
    pid = None

    def for_each_window(hwnd, _):
        nonlocal pid
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            if title in buff.value:
                target_pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(target_pid))
                pid = target_pid.value
                logger.trace(f'{title=} {pid=}')
        return True

    proc = EnumWindowsProc(for_each_window)
    user32.EnumWindows(proc, 0)
    return pid


def find_pid_by_process_name(name=None, name_re=None):
    pid = None if not name_re else []

    def for_each_window(hwnd, _):
        nonlocal pid
        process_name = get_window_thread_process_name(hwnd)
        if (not name_re and name in process_name) or (not name and re.search(name_re, process_name, re.I)):
            target_pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(target_pid))
            pid_value = target_pid.value
            if name:
                pid = pid_value
            else:
                pid.append(pid_value)
            # print(process_name, pid_value)
        return True

    proc = EnumWindowsProc(for_each_window)
    user32.EnumWindows(proc, 0)
    return pid


def get_window_thread_process_name(hwnd):
    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.pointer(pid))
    handle = kernel32.OpenProcess(0x1000, 0, pid)
    try:
        buffer_len = ctypes.c_ulong(1024)
        buffer = ctypes.create_unicode_buffer(buffer_len.value)
        kernel32.QueryFullProcessImageNameW(handle, 0, ctypes.pointer(buffer), ctypes.pointer(buffer_len))
        buffer = buffer[:]
        buffer = buffer[:buffer.index('\0')]
    except Exception as e:
        logger.error(f'get_window_thread_process_name: error {str(e)[:50]}')
    finally:
        if handle:
            kernel32.CloseHandle(handle)
    return str(buffer)
