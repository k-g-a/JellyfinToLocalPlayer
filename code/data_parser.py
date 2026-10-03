import os
import urllib.parse

from code.configs import configs, MyLogger
from code.net_tools import requests_urllib, get_redirect_url
from code.tools import (show_version_info, main_ep_to_title, main_ep_intro_time, logger_setup,
                         sub_via_other_media_version, force_disk_mode_by_path,
                         translate_path_by_ini, debug_beep_win32)

logger = MyLogger()


def _get_sub_order_by_ini(_sub_list):
    for _sub in _sub_list:
        _sub['Order'] = configs.check_str_match(
            f"{str(_sub.get('Title', '') + ',' + _sub['DisplayTitle']).lower()}",
            'dev', 'subtitle_priority', log=False, order_only=True)


def subtitle_checker(media_streams, sub_index, mount_disk_mode, log=False):
    sub_inner_idx = 0
    sub_dict = {}
    # sub_index >= 0 subtitle selected; -1 subtitle not selected; -3 used in playlists to only check external subtitles, embedded subtitles are decided by the player itself
    sub_dict_list = [s for s in media_streams if s['Type'] == 'Subtitle']
    sub_ext_list = [s for s in sub_dict_list if s['IsExternal']]
    sub_inner_list = [s for s in sub_dict_list if not s['IsExternal']]

    if sub_index == -1 and not sub_ext_list and sub_inner_list:
        _get_sub_order_by_ini(sub_inner_list)
        sub_inner_match = [i for i in sub_inner_list if i['Order'] != 0]
        if sub_inner_match:  # may affect the subtitle order when supplementing alternatives for multiple versions, not a big issue, leave it for now.
            sub_inner_match.sort(key=lambda s: s['Order'])
            sub_inner_match = sub_inner_match[0]
            sub_inner_idx = sub_inner_list.index(sub_inner_match) + 1
            log and logger.info(
                f"subtitles: cuz unspecified and not external -> subtitle_priority: --sid={sub_inner_idx} "
                f"(mpv only): {sub_inner_match.get('Title', '')},{sub_inner_match['DisplayTitle']}")

    if sub_index >= 0:
        sub_dict = media_streams[sub_index]
        select_external = sub_dict.get('IsExternal')
        if not select_external:
            sub_inner_idx = sub_inner_list.index(sub_dict) + 1
        if select_external and mount_disk_mode:
            sub_dict = {}

    if sub_index in (-1, -3) and not mount_disk_mode:
        _get_sub_order_by_ini(sub_ext_list)
        sub_ext_list = [i for i in sub_ext_list if i['Order'] != 0]
        sub_ext_list.sort(key=lambda s: s['Order'])
        sub_dict = sub_ext_list[0] if sub_ext_list else {}
        sub_index = sub_dict.get('Index', sub_index)

    return sub_index, sub_inner_idx, sub_dict

def parse_received_data_jellyfin(received_data):
    extra_data = received_data['extraData']
    show_version_info(extra_data=extra_data)
    main_ep_info = extra_data['mainEpInfo']
    episodes_info = extra_data.get('episodesInfo') or []
    playlist_info = extra_data.get('playlistInfo') or []
    jellyfin_title = main_ep_to_title(main_ep_info) if not playlist_info else None
    intro_time = main_ep_intro_time(main_ep_info)
    api_client = received_data['ApiClient']
    url = urllib.parse.urlparse(received_data['playbackUrl'])
    headers = received_data['request'].get('headers', {})
    if extra_data.get('serverName', 'jellyfin') != 'jellyfin':
        raise ValueError('Only Jellyfin playback is supported')
    jellyfin_auth = (headers.get('X-Emby-Authorization', headers.get('Authorization')) or '')
    jellyfin_auth = [i.replace('\'', '').replace('"', '').strip().split('=')
                     for i in jellyfin_auth.split(',')]
    jellyfin_auth = dict((i[0], i[1]) for i in jellyfin_auth if len(i) == 2)

    query = dict(urllib.parse.parse_qsl(url.query))
    query: dict
    item_id = [str(i) for i in url.path.split('/')]
    item_id = item_id[item_id.index('Items') + 1]
    media_source_id = query.get('MediaSourceId')
    header_api_key = headers.get('X-Emby-Token', headers.get('x-emby-token'))
    api_key = query.get('X-Emby-Token') or jellyfin_auth.get('Token') or header_api_key
    scheme, netloc = api_client['_serverAddress'].split('://')
    header_device_id = headers.get('X-Emby-Device-Id', headers.get('x-emby-device-id'))
    device_id = query.get('X-Emby-Device-Id') or jellyfin_auth.get('DeviceId') or header_device_id
    sub_index = int(query.get('SubtitleStreamIndex', -1))
    logger_setup(api_key=api_key, netloc=netloc)

    data = received_data['playbackData']
    media_sources = data['MediaSources']
    play_session_id = data['PlaySessionId']
    if media_source_id and media_source_id != 'undefined': # jellyfin 10.10.6
        media_source_info = [i for i in media_sources if i['Id'] == media_source_id][0]
    else:
        media_source_info = media_sources[0]
        media_source_id = media_source_info['Id']
    # For strm with multiple versions, the server file path of other versions seemingly can't be found, requiring an extra request for episode data. But disk-reading mode isn't needed, so that's fine.
    # Therefore, when strm has multiple versions and is_http_source, playback is correct, but the file title only has one form; not handled for now.
    source_path = media_source_info['Path']  # for strm, this differs from file_path; it's the address text inside the strm
    file_path = source_path if main_ep_info.get('Type') == 'TvChannel' else  main_ep_info['Path']  # incorrect for multiple versions, not an issue for live streams.
    is_strm = file_path != source_path and file_path.endswith('.strm') or media_source_info.get('Container') == 'strm'
    is_http_source =  source_path.startswith('http')
    strm_direct = configs.check_str_match(netloc, 'dev', 'strm_direct_host', log_by=True)
    if not is_strm or (is_strm and not is_http_source):
        file_path = source_path

    if is_strm and is_http_source and len(media_sources) > 1 and media_source_info['Name'] not in file_path:
        source_map = {
            s['Id']: i['Path']
            for i in episodes_info
            for s in i.get('MediaSources', [])
        }  # Use source IDs from the injector metadata to preserve exact paths.
        if media_source_id in source_map:
            file_path = source_map[media_source_id]
        else:
            basename = os.path.basename(file_path)
            # Cases like Season 0/S0E04-ver-a.strm and Specials/S0E04-ver-b.strm can also cause the path folder name to be assembled incorrectly.
            for _m in media_sources:
                if _m['Name'] in basename:  # a case like S01E01.mkv is unsolvable
                    file_path = file_path.replace(_m['Name'], media_source_info['Name'])
                    break

    # stream_url = f'{scheme}://{netloc}{media_source_info["DirectStreamUrl"]}' # may be a transcoded link
    basename = os.path.basename(file_path)
    container = os.path.splitext(file_path)[-1]
    server_version = api_client['_serverVersion']
    stream_name = 'stream'
    if media_source_info.get('VideoType') == 'BluRay':  # jellyfin
        stream_name = 'main'
        container = '.m3u8'
        logger.info('WARNING: bluray bdmv found, may trigger transcode')
    stream_url = f'{scheme}://{netloc}/videos/{item_id}/{stream_name}{container}' \
                 f'?DeviceId={device_id}&MediaSourceId={media_source_id}' \
                 f'&PlaySessionId={play_session_id}&api_key={api_key}&Static=true'
    stream_netloc = netloc
    if is_http_direct_strm := is_strm and strm_direct and is_http_source:
        stream_url = source_path
        stream_netloc = urllib.parse.urlparse(stream_url).netloc

    mount_disk_mode = received_data['mountDiskEnable'] == 'true'
    if not mount_disk_mode or is_http_direct_strm:
        stream_url = configs.string_replace_by_ini_pair(stream_url, 'dev', 'stream_redirect')

        if configs.check_str_match(stream_netloc, 'dev', 'redirect_check_host'):
            _stream_url = get_redirect_url(stream_url)
            if stream_url != _stream_url:
                logger.info(f'url redirect found {stream_url}')
                stream_url = _stream_url

        if configs.check_str_match(stream_netloc, 'dev', 'stream_prefix', log=False):
            stream_prefix = configs.ini_str_split('dev', 'stream_prefix')[0].strip('/')
            stream_url = f'{stream_prefix}{stream_url}'

    if is_strm and not strm_direct or is_http_source:
        mount_disk_mode = False
    if not is_http_source and force_disk_mode_by_path(file_path):
        mount_disk_mode = True
    if is_strm and not is_http_source:
        if strm_direct:
            mount_disk_mode = True
        hint = '\nyou may want to set strm_direct_host in ini' if not strm_direct else ''
        logger.info(f'{source_path=}{hint}')

    if mount_disk_mode:  # definitely won't be http
        if is_strm:
            if strm_direct:
                media_path = translate_path_by_ini(source_path)
            else:  # strm files can't be played directly
                media_path = stream_url
                mount_disk_mode = False
        else:
            media_path = translate_path_by_ini(file_path)
    else:
        if is_strm and strm_direct and not is_http_direct_strm:
            media_path = source_path
        else:
            media_path = stream_url

    media_streams = media_source_info['MediaStreams']
    # mpv can pass the selected index of the first episode's embedded subtitle; other players decide this by their own rules.
    sub_index, sub_inner_idx, sub_dict = subtitle_checker(media_streams, sub_index, mount_disk_mode, log=True)
    sub_jellyfin_str = f'{item_id[:8]}-{item_id[8:12]}-{item_id[12:16]}-{item_id[16:20]}-{item_id[20:]}/'
    if sub_dict and sub_inner_idx == 0:

        # sub_data = media_source_info['MediaStreams'][sub_index]
        fallback_sub = f'/videos/{sub_jellyfin_str}{item_id}/Subtitles' \
                       f'/{sub_index}/0/Stream.{sub_dict["Codec"]}?api_key={api_key}'
        # pot 240618 doesn't support Jellyfin DeliveryUrl's vtt format, which is actually srt.
        sub_delivery_url = sub_dict['Codec'] not in ('sup', 'srt') and sub_dict.get('DeliveryUrl') or fallback_sub
    else:
        sub_delivery_url = None

    if not sub_delivery_url and configs.raw.get('dev', 'sub_extract_priority', fallback='') and main_ep_info:
        if sub_all_match := sub_via_other_media_version(main_ep_info['MediaSources']):
            _sub_source_id, _sub_index, _sub_codec = list(sub_all_match.values())[0]
            if not sub_all_match.get(media_source_id):

                sub_delivery_url = f'/videos/{sub_jellyfin_str}{item_id}/Subtitles' \
                                   f'/{_sub_index}/0/Stream.{_sub_codec}?api_key={api_key}'
                logger.info(f'other version sub found, url={sub_delivery_url}')
    sub_file = f'{scheme}://{netloc}{sub_delivery_url}' if sub_delivery_url else None
    if '.m3u8' in file_path:
        media_path = stream_url = file_path

    pretty_title = configs.raw.getboolean('dev', 'pretty_title', fallback=True)
    media_title = f'{jellyfin_title}  |  {basename}' if pretty_title and jellyfin_title else basename
    title_trans = configs.media_title_translate(get_trans=True)
    if title_trans:
        media_title = media_title.translate(title_trans)
        _title_trans = {chr(k): v for k, v in title_trans.items()}
        logger.info(f'media_title_translate {_title_trans}')

    seek = query['StartTimeTicks']
    start_sec = int(seek) // (10 ** 7) if seek else 0
    server = 'jellyfin'

    fake_name = os.path.splitdrive(file_path)[1].replace('/', '__').replace('\\', '__')
    total_sec = int(media_source_info.get('RunTimeTicks', 0)) // 10 ** 7 or 3600 * 24
    position = start_sec / total_sec
    user_id = query['UserId']
    media_basename = os.path.basename(media_path)
    size = int(media_source_info.get('Size', 0)) or 0

    result = dict(
        server=server,
        mount_disk_mode=mount_disk_mode,
        api_key=api_key,
        scheme=scheme,
        netloc=netloc,
        media_path=media_path,
        start_sec=start_sec,
        sub_file=sub_file,
        media_title=media_title,
        play_session_id=play_session_id,
        device_id=device_id,
        headers=headers,
        item_id=item_id,
        media_source_id=media_source_id,
        file_path=file_path,
        stream_url=stream_url,
        fake_name=fake_name,
        position=position,
        total_sec=total_sec,
        user_id=user_id,
        basename=basename,
        media_basename=media_basename,
        main_ep_info=main_ep_info,
        episodes_info=episodes_info,
        playlist_info=playlist_info,
        intro_start=intro_time.get('intro_start'),
        intro_end=intro_time.get('intro_end'),
        server_version=server_version,
        is_strm=is_strm,
        strm_direct=strm_direct,
        is_http_source=is_http_source,
        source_path=source_path,
        is_http_direct_strm=is_http_direct_strm,
        sub_inner_idx=sub_inner_idx,
        size=size,
    )
    return result


def list_playlist_or_mix_s0(data):
    scheme = data['scheme']
    netloc = data['netloc']
    api_key = data['api_key']
    user_id = data['user_id']
    device_id, play_session_id = data['device_id'], data['play_session_id']
    playlist_info = data['playlist_info']  # movie or music video
    episodes_info = data['episodes_info']  # may be a mix of correct episode numbers with S0

    params = {'X-Emby-Token': api_key, }
    headers = {'accept': 'application/json', }
    headers.update(data['headers'])

    ids = [ep['Id'] for ep in playlist_info]
    params.update({'Fields': 'MediaSources,Path,ProviderIds',
                   'Ids': ','.join(ids), })
    playlist_data = requests_urllib(
        f'{scheme}://{netloc}/Users/{user_id}/Items',
        params=params, headers=headers, get_json=True)
    return playlist_data


def list_episodes(data: dict):
    scheme = data['scheme']
    netloc = data['netloc']
    api_key = data['api_key']
    user_id = data['user_id']
    mount_disk_mode = data['mount_disk_mode']
    device_id, play_session_id = data['device_id'], data['play_session_id']

    params = {'X-Emby-Token': api_key, }
    headers = {'accept': 'application/json', }
    headers.update(data['headers'])

    playlist_info = data.get('playlist_info')
    playlist_info and logger.info('playlist_info found, skip version filter and pretty title')
    main_ep_info = data.get('main_ep_info') or requests_urllib(
        f'{scheme}://{netloc}/Users/{user_id}/Items/{data["item_id"]}',
        params=params, headers=headers, get_json=True)

    def fill_data_type_provider_ids(): # sync trakt required
        data.update(main_ep_info)
        return data

    # if video is movie
    if not playlist_info and 'SeasonId' not in main_ep_info:
        return [fill_data_type_provider_ids()]
    season_id = main_ep_info.get('SeasonId')
    stream_name = 'stream'

    main_ep_basename = data['basename']
    is_strm = data['is_strm']
    is_http_source = data['is_http_source']
    strm_direct = data['strm_direct']
    is_http_direct_strm = data['is_http_direct_strm']

    def strm_file_name_sync(file_path, episodes_data):
        if is_strm and not is_http_source:
            for i in episodes_data:
                i['Path'] = i['MediaSources'][0]['Path']

        return episodes_data


    title_intro_map_fail = False

    def title_intro_index_map():
        nonlocal title_intro_map_fail
        _res = _title_map, _start_map, _end_map = {}, {}, {}
        if playlist_info:
            return _res
        episodes_info = data.get('episodes_info') or []
        title_intro_map_fail = not episodes_info

        for ep in episodes_info:
            if ep['SeasonId'] != season_id:  # affects S0 mixed playback, used too rarely, not handled for now
                continue
            if 'ParentIndexNumber' not in ep or 'IndexNumber' not in ep:
                title_intro_map_fail = True
                logger.info('disable title_intro_index_map, cuz season or ep index num error found')
                return _res
            if 'IndexNumberEnd' in ep:
                _t = f"{ep['SeriesName']} S{ep['ParentIndexNumber']}" \
                     f":E{ep['IndexNumber']}-{ep['IndexNumberEnd']} - {ep['Name']}"
            else:
                _t = f"{ep['SeriesName']} S{ep['ParentIndexNumber']}:E{ep['IndexNumber']} - {ep['Name']}"
            _key = f"{ep['ParentIndexNumber']}-{ep['IndexNumber']}"
            _title_map[_key] = _t

            if not ep.get('Chapters'):
                continue
            chapters = [i for i in ep['Chapters'][:5] if i.get('MarkerType')
                        and not str(i['StartPositionTicks']).endswith('000000000')
                        and not (i['StartPositionTicks'] == 0 and i['MarkerType'] == 'Chapter')]
            if not chapters or len(chapters) > 2:
                continue
            for i in chapters:
                if i['MarkerType'] == 'IntroStart':
                    _start_map[_key] = i['StartPositionTicks'] // (10 ** 7)
                elif i['MarkerType'] == 'IntroEnd':
                    _end_map[_key] = i['StartPositionTicks'] // (10 ** 7)

        return _res

    title_data, start_data, end_data = title_intro_index_map()
    pretty_title = configs.raw.getboolean('dev', 'pretty_title', fallback=True)
    need_check_inner_sub = {True: -1, False: -3}[bool(data.get('sub_inner_idx'))]

    def parse_item(item, order):
        source_info = item['MediaSources'][0]
        media_source_id = source_info["Id"]
        file_path = item['Path']
        source_path = source_info['Path']
        fake_name = os.path.splitdrive(file_path)[1].replace('/', '__').replace('\\', '__')
        item_id = item['Id']
        container = os.path.splitext(file_path)[-1]
        stream_url = f'{scheme}://{netloc}/videos/{item_id}/{stream_name}{container}' \
                     f'?DeviceId={device_id}&MediaSourceId={media_source_id}' \
                     f'&PlaySessionId={play_session_id}&api_key={api_key}&Static=true'
        if is_http_direct_strm:
            stream_url = source_path

        if mount_disk_mode:  # definitely won't be http
            if is_strm:
                if strm_direct:
                    media_path = translate_path_by_ini(source_path)
                else:  # strm files can't be played directly
                    media_path = stream_url
            else:
                media_path = translate_path_by_ini(file_path)
        else:
            if is_strm and strm_direct and not is_http_direct_strm:
                media_path = source_path
            else:
                media_path = stream_url

        basename = os.path.basename(file_path)
        index = item.get('IndexNumber', 0)
        unique_key = f"{item.get('ParentIndexNumber')}-{index}"
        jellyfin_title = title_data.get(unique_key)
        media_title = f'{jellyfin_title}  |  {basename}' if pretty_title and jellyfin_title else basename
        media_title = media_title.replace('"', '”')
        media_basename = os.path.basename(media_path)
        total_sec = int(source_info.get('RunTimeTicks', 0)) // 10 ** 7 or 3600 * 24
        size = int(source_info.get('Size', 0)) or 0

        media_streams = source_info['MediaStreams']
        sub_index, sub_inner_idx, sub_dict = subtitle_checker(media_streams, need_check_inner_sub, mount_disk_mode)

        sub_file = None
        if sub_dict and sub_inner_idx == 0:
            sub_file = f'{scheme}://{netloc}/Videos/{item_id}/{source_info["Id"]}/Subtitles' \
                       f'/{sub_dict["Index"]}/Stream{os.path.splitext(sub_dict["Path"])[-1]}'

        result = data.copy()
        result['Type'] = item['Type']
        result['ProviderIds'] = item['ProviderIds']
        result['ParentIndexNumber'] = item.get('ParentIndexNumber')
        if not playlist_info:
            result['SeriesId'] = item['SeriesId']
            result['SeasonId'] = season_id
        if basename != main_ep_basename:
            for none_key in ['start_sec', 'main_ep_info', 'episodes_info']:
                result[none_key] = None
        else:
            # Because of different library-add times, the Jellyfin title of ver_a and ver_b for the same episode may differ; the web page only shows ver_a's.
            # The starting episode's title is fixed to ver_a, but with version_prefer, the actually played and listed data may be b, causing reporting to fail.
            media_title = data['media_title']
        result.update(dict(
            basename=basename,
            media_basename=media_basename,
            item_id=item_id,
            media_source_id=media_source_id,
            file_path=file_path,
            stream_url=stream_url,
            media_path=media_path,
            fake_name=fake_name,
            total_sec=total_sec,
            sub_file=sub_file,
            index=index,
            size=size,  # Jellyfin strm doesn't have this key
            media_title=media_title,
            intro_start=start_data.get(unique_key),
            intro_end=end_data.get(unique_key),
            order=order,
            sub_inner_idx=sub_inner_idx,
        ))
        return result

    if playlist_info:
        # jellyfin extras/specials seem to also be treated as playlist data.
        def chunk_list(lst, chunk_size):
            for i in range(0, len(lst), chunk_size):
                yield lst[i:i + chunk_size]
        # limit the number of random playlist entries to avoid HTTP Error 414: URI Too Long
        ids = [ep['Id'] for ep in playlist_info][:200]
        _eps_parts = []
        for _ids in chunk_list(ids, 200):
            params.update({'Fields': 'MediaSources,Path,ProviderIds',
                           'Ids': ','.join(_ids), })
            _episodes = requests_urllib(
                f'{scheme}://{netloc}/Users/{user_id}/Items',
                params=params, headers=headers, get_json=True)
            _eps_parts.append(_episodes)
        episodes = _eps_parts[0]
        if len(_eps_parts) > 1:
            for _part in _eps_parts[1:]:
                episodes['Items'].extend(_part['Items'])
            logger.info(f'playlist_info items count: {len(ids)}, may too large')

    else:
        params.update({'Fields': 'MediaSources,Path,ProviderIds',
                       'SeasonId': season_id, })
        series_id = main_ep_info['SeriesId']
        if not season_id:  # Jellyfin 10.10.7 unknown season: mainEpInfo is missing the season id, causing the request to fail. 10.9.11 and 10.11.1 are fine.
            season_id = series_id
            del params['SeasonId']
            logger.info('playlist: season_id not found fallback to series_id, may leak error')
        # Switched to season_id to avoid failing to prettify the title due to non-standard S0 naming; unsure whether this affects S0 mixed playback.
        url = f'{scheme}://{netloc}/Shows/{season_id}/Episodes'
        episodes = requests_urllib(url, params=params, headers=headers, get_json=True)
    # dump_json_file(episodes, 'z_playlist_movie.json')
    eps_error = [i for i in episodes['Items'] if 'Path' not in i or 'RunTimeTicks' not in i]
    path_error = [i for i in eps_error if 'Path' not in i]
    if eps_error:
        # No total_sec, hard to determine progress.
        ids_error = [i['MediaSources'][0]['Id'] for i in path_error]
        try:
            eps_error = [f"E{i['IndexNumber']}-{i['Name']}-id={i['Id']}" for i in eps_error]
        except KeyError:
            logger.error('disable playlist, IndexNumber miss')
            return [fill_data_type_provider_ids()]
        logger.error(f'some ep miss path or runtime data, may leak error\n{eps_error}')
        if data['media_source_id'] in ids_error:
            logger.error(f'disable playlist, Path miss')
            return [fill_data_type_provider_ids()]

    episodes = [i for i in episodes['Items'] if 'Path' in i]
    episodes = strm_file_name_sync(data['file_path'], episodes)
    episodes = [parse_item(i, o) for (o, i) in enumerate(episodes)]

    if title_intro_map_fail:
        debug_beep_win32()
        logger.info('pretty title: title_intro_map_fail')
        _file_path = data['file_path']
        for ep in episodes:
            if ep['file_path'] == _file_path:
                ep['media_title'] = data['media_title']

    stream_redirect = configs.check_str_match(episodes[0]['stream_url'], 'dev', 'stream_redirect', get_pair=True)
    title_trans = configs.media_title_translate(get_trans=True, log=False)
    if stream_redirect or title_trans:
        for i in episodes:
            if stream_redirect:
                i['stream_url'] = i['stream_url'].replace(stream_redirect[0], stream_redirect[1])
                if not mount_disk_mode:
                    i['media_path'] = i['stream_url']
            if title_trans:
                i['media_title'] = i['media_title'].translate(title_trans)

    if configs.check_str_match(netloc, 'dev', 'stream_prefix', log=False):
        stream_prefix = configs.ini_str_split('dev', 'stream_prefix')[0].strip('/')
        for i in episodes:
            if i['stream_url'].startswith(stream_prefix):
                continue
            i['stream_url'] = f"{stream_prefix}{i['stream_url']}"
            if not mount_disk_mode:
                i['media_path'] = i['stream_url']

    return episodes
