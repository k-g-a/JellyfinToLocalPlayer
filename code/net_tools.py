import json
import os.path
import re
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Union

from code.configs import configs, MyLogger

ssl_context = ssl.SSLContext() if configs.raw.getboolean('dev', 'skip_certificate_verify', fallback=False) else None
sync_third_party_done_ids = {'trakt': [],
                             'simkl': []}

logger = MyLogger()
redirect_url_cache = {}


def safe_url(url):
    parts = urllib.parse.urlsplit(url)
    quoted_path = urllib.parse.quote(parts.path, safe="/%")
    return urllib.parse.urlunsplit((
        parts.scheme,
        parts.netloc,
        quoted_path,
        parts.query,
        parts.fragment,
    ))


def requests_urllib(host, params=None, _json=None, decode=False, timeout=5.0, headers=None, req_only=False,
                    http_proxy='', get_json=False, save_path='', retry=5, silence=False, res_only=False,
                    method=None):
    _json = json.dumps(_json).encode('utf-8') if _json else None
    params = urllib.parse.urlencode(params) if params else None
    host = host + '?' + params if params else host
    host = safe_url(host)
    req = urllib.request.Request(host, method=method)
    http_proxy = http_proxy or configs.script_proxy
    if http_proxy and not host.startswith(('http://127.0.0.1', 'http://localhost')):
        req.set_proxy(http_proxy, 'http')
        if host.startswith('https'):
            req.set_proxy(http_proxy, 'https')
    req.add_header('User-Agent', 'JellyfinToLocalPlayer/1.1')
    headers and [req.add_header(k, v) for k, v in headers.items()]
    if _json or get_json:
        req.add_header('Content-Type', 'application/json; charset=utf-8')
        req.add_header('Accept', 'application/json')
    if req_only:
        return req

    response = None
    for try_times in range(1, retry + 1):
        try:
            response = urllib.request.urlopen(req, _json, timeout=timeout, context=ssl_context)
            if res_only:
                return response
            break
        except socket.timeout:
            logger.error(f'urllib timeout {try_times=} {host=}', silence=silence)
            if try_times == retry:
                raise TimeoutError(f'{try_times=} {host=}') from None
        except urllib.error.URLError as e:
            logger.error(f'urllib {try_times=} {host=}\n{str(e)[:100]}', silence=silence)
            if try_times == retry:
                raise ConnectionError(f'{try_times=} {host=} \n{str(e)[:100]}') from None
    if decode:
        return response.read().decode()
    if get_json:
        return json.loads(response.read().decode())
    if save_path:
        folder = os.path.dirname(save_path)
        if not os.path.exists(folder):
            os.mkdir(folder)
        with open(save_path, 'wb') as f:
            f.write(response.read())
        return save_path


class SkipHTTPRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, hdrs, newurl):
        return


class FollowHTTPRedirectHandler(urllib.request.HTTPRedirectHandler):
    def http_error_301(self, req, fp, code, msg, hdrs):
        # Avoid duplicate 301, reason unknown
        return


def check_miss_runtime_start_sec(netloc, item_id, basename, start_sec=0, stop_sec=None):
    href = configs.raw.get('dev', 'server_side_href', fallback='').strip().strip('/')
    href = href or configs.local_server_url
    url = f'{href}/miss_runtime_start_sec'
    params = {'netloc': netloc, 'item_id': item_id, 'basename': basename}
    get_json = True
    if stop_sec is not None:
        params['stop_sec'] = stop_sec
        get_json = False
    try:
        res = requests_urllib(url, params=params, get_json=get_json, timeout=3, retry=3)
        if res and start_sec == 0:
            return res['start_sec']
    except Exception:
        logger.info('check_miss_runtime: can not connect to server, check server_side_href setting')


def check_redirect_cache_expired_loop():
    redirect_time = {}
    ini_dict = configs.get_match_value('', 'dev', 'redirect_expire_minute', get_ini_dict=True)
    if not ini_dict:
        return
    ini_dict = {k:int(v) for k,v in ini_dict.items()}
    logger.info(f'redirect_cache_expire: {ini_dict}')
    pattern = re.compile('|'.join(ini_dict.keys()))
    while True:
        now = time.time()
        for url in list(redirect_url_cache.keys()):
            match = pattern.search(url)
            if not match:
                continue
            if before := redirect_time.get(url):
                expire = ini_dict[match[0]] * 60
                if (before + expire) < now:
                    del redirect_url_cache[url]
                    del redirect_time[url]
                    logger.info(f'redirect_cache_expired: {url}')
            else:
                redirect_time[url] = now
                continue

        time.sleep(300)


def get_redirect_url(url, key_trim='PlaySessionId', follow_redirect=False):
    jump_url = url
    key = url.split(key_trim)[0] if key_trim else url
    if cache := redirect_url_cache.get(key):
        return cache
    start = time.time()
    try:
        redirect_handler = FollowHTTPRedirectHandler if follow_redirect else SkipHTTPRedirectHandler
        # FollowHTTPRedirectHandler, # system proxy can be slow, not enabled by default
        timeout = 30 if follow_redirect else 5
        handlers = [
            urllib.request.HTTPSHandler(context=ssl_context),
            redirect_handler,
        ]
        opener = urllib.request.build_opener(*handlers)
        jump_url = opener.open(requests_urllib(url, req_only=True), timeout=timeout).url
    except urllib.error.HTTPError as e:
        if e.code in [301, 302]:
            jump_url = e.headers['Location'] if e.url == url else e.url
        else:
            logger.error(f'{e.code=} get_redirect_url: {str(e)[:100]}')
            jump_url = e.url
    except Exception as e:
        logger.error(f'disable redirect: code={getattr(e, "code", None)} get_redirect_url: {str(e)[:100]}')
    _log = f'get_redirect_url: used time={str(time.time() - start)[:4]}'
    if jump_url != url:
        logger.info(f'{_log} success')
        redirect_url_cache[key] = jump_url
    else:
        logger.info(f'{_log} fail\nredirect not found, may need to disable it')
    return jump_url


def multi_thread_requests(urls: Union[list, tuple, dict], **kwargs):
    return_list = False

    def dict_requests(key, url):
        return {key: requests_urllib(host=url, **kwargs)}

    if not isinstance(urls, dict):
        return_list = True
        urls = dict(zip(range(len(urls)), urls))

    result = {}
    with ThreadPoolExecutor(max_workers=20) as executor:
        for future in as_completed([executor.submit(dict_requests, key, url) for (key, url) in urls.items()]):
            result.update(future.result())
    if return_list:
        return [i[1] for i in sorted(result.items())]
    return result


def change_jellyfin_play_position(scheme, netloc, item_id, stop_sec, play_session_id, headers, **kwargs):
    if stop_sec > 10 * 60 * 60:
        logger.error('stop_sec error, check it')
        return
    ticks = stop_sec * 10 ** 7
    if not kwargs.get('update_success'):  # marked by the real-time playback reporting feature
        # If this request is omitted, newer Jellyfin versions will put new "continue watching" entries at the end.
        requests_urllib(f'{scheme}://{netloc}/Sessions/Playing',
                        headers=headers,
                        _json={
                            'ItemId': item_id,
                            'PlaySessionId': play_session_id,
                        })
    requests_urllib(f'{scheme}://{netloc}/Sessions/Playing/Stopped',
                    headers=headers,
                    _json={
                        'PositionTicks': ticks,
                        'ItemId': item_id,
                        'PlaySessionId': play_session_id,
                    })


def realtime_playing_request_sender(data, cur_sec, method='playing'):
    ticks = int(cur_sec * 10 ** 7)
    url_path = {
        'start': 'Sessions/Playing',
        'playing': 'Sessions/Playing/Progress',
        'end': 'Sessions/Playing/Stopped',
    }[method]
    params = {
        'X-Emby-Token': data['api_key'],
        'X-Emby-Device-Id': data['device_id'],
        'X-Emby-Device-Name': 'JellyfinToLocalPlayer',
    }
    _json = {
        'EventName': 'timeupdate',
        'ItemId': data['item_id'],
        'MediaSourceId': data['media_source_id'],
        'PlayMethod': 'DirectStream',
        'PlaySessionId': data['play_session_id'],
        'PositionTicks': ticks,
        'RepeatMode': 'RepeatNone',
    }
    try:
        requests_urllib(f'{data["scheme"]}://{data["netloc"]}/{url_path}',
                        params=params,
                        _json=_json,
                        headers=data['headers'],
                        timeout=10)
    except Exception:
        time.sleep(30)
        pass


def update_server_playback_progress(stop_sec, data):
    if not configs.raw.getboolean('jellyfin', 'update_progress', fallback=True):
        return
    if stop_sec is None:
        logger.error('stop_sec is None skip update progress')
        return
    file_path = data['file_path']
    ext = os.path.splitext(file_path)[-1].lower()
    # iso reporting will be marked as watched.
    normal_file = False if ext.endswith(('.iso', '.m3u8')) else True
    stop_sec = int(stop_sec)
    stop_sec = stop_sec - 2 if stop_sec > 5 else stop_sec

    if not normal_file:
        logger.info(f'skip update progress because media is {ext}')
        return
    change_jellyfin_play_position(stop_sec=stop_sec, **data)
    logger.info(f'update progress: {data["basename"]} {stop_sec=}')


def sync_third_party_for_eps(eps, provider):
    if not eps:
        return
    if not configs.check_str_match(eps[0]['netloc'], provider, 'enable_host', log=True):
        return
    useful_items = []
    for ep in eps:
        item_id = ep['item_id']
        if item_id in sync_third_party_done_ids[provider]:
            logger.info(f"{provider}: skip, cuz updated previously. {ep['basename']}")
            continue
        if ep['_stop_sec'] / ep['total_sec'] > 0.9:
            sync_third_party_done_ids[provider].append(item_id)
            useful_items.append(ep)
    if not useful_items:
        return

    if provider == 'trakt':
        from code.trakt_sync import trakt_sync_main
        trakt_sync_main(eps_data=useful_items)

    if provider == 'simkl':
        from code.simkl_sync import simkl_sync_main
        simkl_sync_main(eps_data=useful_items)

def save_sub_file(url, name='tmp_sub.srt'):
    srt = os.path.join(configs.tmp_dir, name)
    requests_urllib(url, save_path=srt)
    return srt
