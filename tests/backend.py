"""Offline regressions for retained playback and the renamed installation layout."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from code.configs import configs
from code import data_parser, net_tools, players, reporting, tools, downloader, player_manager
from code.jellyfin_api import JellyfinApi
from code.jellyfin_api_thin import JellyfinApiThin
from code.simkl_sync import simkl_sync_main
from code.trakt_sync import trakt_sync_main
from code.update import install_archive, RELEASE_URL

ITEM = '0123456789abcdef0123456789abcdef'


def payload():
    source = {'Id': 'source-a', 'Path': '/media/Film (2020) [imdbid-tt123].mkv',
              'Name': 'Film', 'MediaStreams': [], 'RunTimeTicks': 1000 * 10**7, 'Size': 2048}
    item = {'Id': ITEM, 'Type': 'Movie', 'Name': 'Film', 'ProductionYear': 2020,
            'Path': source['Path'], 'ProviderIds': {'Imdb': 'tt123'}, 'MediaSources': [source]}
    return {
        'extraData': {'serverName': 'jellyfin', 'mainEpInfo': item, 'injectorVersion': '4.0.0'},
        'ApiClient': {'_serverAddress': 'http://jellyfin.test:8096', '_serverVersion': '12.1.0'},
        'playbackUrl': f'http://jellyfin.test:8096/Items/{ITEM}/PlaybackInfo?UserId=user&StartTimeTicks=420000000',
        'request': {'headers': {'Authorization': 'MediaBrowser Client="Web", Token="token", DeviceId="device"'}},
        'playbackData': {'MediaSources': [source], 'PlaySessionId': 'session'},
        'mountDiskEnable': 'false',
    }


class PlaybackTests(unittest.TestCase):
    def setUp(self):
        self.raw = configs.raw
        configs.raw = copy.deepcopy(self.raw)
        configs.raw['dev']['use_system_proxy'] = 'no'
        configs.raw['dev']['media_title_translate'] = ''
        self.addCleanup(setattr, configs, 'raw', self.raw)

    def test_network_source_resume_and_final_progress(self):
        data = data_parser.parse_received_data_jellyfin(payload())
        self.assertEqual(data['server'], 'jellyfin')
        self.assertEqual(data['start_sec'], 42)
        self.assertEqual(data['api_key'], 'token')
        self.assertEqual(data['device_id'], 'device')
        self.assertIn(f'/videos/{ITEM}/stream.mkv?', data['media_path'])
        self.assertEqual(data['file_path'], payload()['extraData']['mainEpInfo']['Path'])
        with patch.object(net_tools, 'requests_urllib') as request:
            net_tools.update_server_playback_progress(980, data)
        self.assertEqual([c.args[0] for c in request.call_args_list], [
            'http://jellyfin.test:8096/Sessions/Playing',
            'http://jellyfin.test:8096/Sessions/Playing/Stopped'])
        self.assertEqual(request.call_args.kwargs['_json']['PositionTicks'], 978 * 10**7)
        self.assertEqual(request.call_args.kwargs['headers'], data['headers'])
        configs.raw['jellyfin']['update_progress'] = 'no'
        with patch.object(net_tools, 'requests_urllib') as request:
            net_tools.update_server_playback_progress(980, data)
            request.assert_not_called()

    def test_local_unicode_path_and_per_instance_player_override(self):
        with tempfile.TemporaryDirectory() as directory:
            filename = '47 ронинов (47 Ronin, 2013) [imdbid-tt1335975].mkv'
            actual = Path(directory) / filename
            actual.touch()
            configs.raw['src'] = {'media': '/media'}
            configs.raw['dst'] = {'media': directory}
            configs.raw['dev']['path_check'] = 'yes'
            configs.raw['exe']['hc'] = 'mpc-hc.exe'
            configs.raw['exe']['be'] = 'mpc-be.exe'
            configs.raw['dev']['player_by_path'] = 'be: Ronin;'
            message = payload()
            message['mountDiskEnable'] = 'true'
            message['playbackData']['MediaSources'][0]['Path'] = '/media/' + filename
            data = data_parser.parse_received_data_jellyfin(message)
            self.assertEqual(data['media_path'], str(actual))
            self.assertEqual(tools.get_player_cmd(data['media_path'], data['file_path'], data),
                             ['mpc-be.exe', str(actual)])

    def test_episode_playlist_keeps_titles_resume_and_selected_subtitle(self):
        message = payload()
        item = message['extraData']['mainEpInfo']
        item.update(Type='Episode', SeriesId='series', SeasonId='season', SeriesName='Series',
                    ParentIndexNumber=1, IndexNumber=1)
        sub = {'Index': 0, 'Type': 'Subtitle', 'IsExternal': False, 'DisplayTitle': 'English', 'Title': 'English'}
        item['MediaSources'][0]['MediaStreams'] = [sub]
        message['playbackUrl'] += '&SubtitleStreamIndex=0'
        second = copy.deepcopy(item)
        second.update(Id='second', Name='Second', IndexNumber=2, Path='/media/Second.mkv')
        second['MediaSources'][0].update(Id='source-b', Path=second['Path'])
        for ep in (item, second):
            ep['RunTimeTicks'] = 1000 * 10**7
        message['extraData']['episodesInfo'] = [item, second]
        configs.raw['dev']['subtitle_priority'] = 'english'
        data = data_parser.parse_received_data_jellyfin(message)
        with patch.object(data_parser, 'requests_urllib', return_value={'Items': [item, second]}) as request:
            episodes = data_parser.list_episodes(data)
        self.assertIn('/Shows/season/Episodes', request.call_args.args[0])
        self.assertEqual([e['item_id'] for e in episodes], [ITEM, 'second'])
        self.assertEqual([e['start_sec'] for e in episodes], [42, None])
        self.assertEqual([e['sub_inner_idx'] for e in episodes], [1, 1])
        self.assertIn('Series S1:E2', episodes[1]['media_title'])
        self.assertIn('MediaSourceId=source-b', episodes[1]['stream_url'])

    def test_subtitles_empty_defaults_and_explicit_external_selection(self):
        configs.raw['dev']['subtitle_priority'] = ''
        external = {'Index': 0, 'Type': 'Subtitle', 'IsExternal': True,
                    'DisplayTitle': 'English', 'Title': '', 'Codec': 'srt'}
        self.assertEqual(data_parser.subtitle_checker([external], -1, False), (-1, 0, {}))
        self.assertEqual(data_parser.subtitle_checker([external], 0, False), (0, 0, external))
        self.assertEqual(data_parser.subtitle_checker([external], 0, True), (0, 0, {}))

    def test_mpc_launch_preserves_resume_subtitle_and_control_port(self):
        with patch.object(players, 'get_pipe_or_port_str', return_value='59000'), \
             patch.object(players.subprocess, 'Popen', return_value=Mock(pid=123)) as launch, \
             patch.object(players, 'activate_window_by_pid'), \
             patch.object(players, 'MPCHttpApi', return_value=Mock()):
            players.mpc_player_start(['mpc-hc.exe', 'http://jellyfin.test/video.mkv'], start_sec=42,
                                     sub_file='http://jellyfin.test/sub.srt')
        command = launch.call_args.args[0]
        self.assertEqual(command[command.index('/start') + 1], '"42000"')
        self.assertEqual(command[command.index('/webport') + 1], '59000')
        self.assertEqual(command[command.index('/sub') + 1], '"http://jellyfin.test/sub.srt"')

    def test_api_clients_use_jellyfin_paths_and_required_headers(self):
        for client in (JellyfinApi('https://jellyfin.test', 'token', 'user'),
                       JellyfinApiThin(host='https://jellyfin.test', api_key='token', user_id='user')):
            self.assertEqual(client.api_url('/Items/item'), 'https://jellyfin.test/Items/item')
        thin = JellyfinApiThin(host='https://jellyfin.test', api_key='token', user_id='user')
        thin.req = Mock(return_value={'Items': []})
        thin.get_resume_items()
        self.assertIn('X-Emby-Authorization', thin.req.call_args.kwargs['headers'])
        configs.raw['dev']['server_data_group'] = 'home, https://jellyfin.test, token, user;'
        self.assertEqual(configs.get_server_api_by_ini()['home'].api_url('Items'), 'https://jellyfin.test/Items')
        configs.raw['dev']['server_data_group'] += 'old, http://old, token, user, emby;'
        with self.assertRaises(ValueError):
            configs.get_server_api_by_ini()

    def test_reporting_helpers_and_trakt_simkl_without_bangumi(self):
        api = Mock(user_id='user')
        watched = {'UserData': {'Played': True}, 'IndexNumber': 2, 'ParentIndexNumber': 1}
        api.get_episodes.return_value = {'Items': [watched, {**watched, 'UserData': {'Played': False}}]}
        self.assertEqual(reporting.get_jellyfin_season_watched_ep_key(api, [{'SeriesId': 's', 'SeasonId': 'season'}]), ['1-2'])
        data = data_parser.parse_received_data_jellyfin(payload())
        data.update(payload()['extraData']['mainEpInfo'])
        simkl = Mock()
        simkl.add_ep_or_movie_to_history.return_value = {'added': {'movies': 1, 'shows': 0, 'episodes': 0, 'statuses': 0}}
        simkl_sync_main(simkl=simkl, jellyfin=api, eps_data=[data])
        self.assertEqual(simkl.add_ep_or_movie_to_history.call_args.kwargs['movies'][0]['ids'], {'imdb': 'tt123'})
        trakt = Mock()
        trakt.id_lookup.return_value = [{'type': 'movie', 'movie': {'ids': {'imdb': 'tt123', 'slug': 'film'}}}]
        trakt.get_watch_history.return_value = []
        trakt_sync_main(trakt=trakt, jellyfin=api, eps_data=[data])
        trakt.add_ep_or_movie_to_history.assert_called_once()
        self.assertFalse(any('bangumi' in name for name in sys.modules))

    def test_both_prefetch_paths_still_issue_requests(self):
        class EndLoop(BaseException):
            pass
        source = payload()['playbackData']['MediaSources'][0]
        ep = {'Id': ITEM, 'Path': source['Path'], 'Name': 'Film'}
        api = Mock(host='http://jellyfin.test', api_key='token')
        api.get_resume_items.return_value = {'Items': [ep]}
        api.get_playback_info.return_value = payload()['playbackData']
        api.api_url.side_effect = lambda path: 'http://jellyfin.test/' + path
        with patch.object(downloader, 'Downloader') as download, \
             patch.object(downloader.time, 'sleep', side_effect=EndLoop):
            with self.assertRaises(EndLoop):
                downloader._prefetch_resume_tv(api, ['/media'])
        self.assertEqual([c.args for c in download.return_value.percent_download.call_args_list], [(0, .05), (.98, 1)])
        configs.raw['playlist'].update(prefetch_percent='50', prefetch_host='jellyfin.test', prefetch_type='sequence')
        first = data_parser.parse_received_data_jellyfin(payload())
        second = {**first, 'item_id': 'second', 'basename': 'Second.mkv'}
        manager = object.__new__(player_manager.PrefetchManager)
        manager.playlist_data = {'first': first, 'second': second}
        manager.player_kwargs = {}
        state = {'on': True, 'stop_sec_dict': {'first': 600}, 'done_list': []}
        with patch.object(player_manager, 'prefetch_data', state), \
             patch.object(player_manager, 'requests_urllib') as request, \
             patch.object(player_manager.time, 'sleep', side_effect=EndLoop):
            with self.assertRaises(EndLoop):
                manager.prefetch_next_ep_loop()
        self.assertEqual(request.call_args.kwargs['_json']['item_id'], 'second')
        self.assertEqual(request.call_args.kwargs['_json']['gui_cmd'], 'download_only')


class UpdaterTests(unittest.TestCase):
    def test_update_preserves_configs_runtime_and_uses_fork(self):
        self.assertIn('k-g-a/JellyfinToLocalPlayer/', RELEASE_URL)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / 'config.ini'
            config.write_text('[jellyfin]\nplayer = be\n')
            custom = root / 'custom.ini'
            custom.write_text('my custom config')
            state = root / '.instances/a/trakt_token.json'
            state.parent.mkdir(parents=True)
            state.write_text('my token')
            archive = root / 'release.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                for name in ('main.py', 'launch.bat', 'code/__init__.py', 'code/configs.py',
                             'scripts/jellyfinToLocalPlayer.injector.js'):
                    z.writestr(name, 'new code')
                z.writestr('config.ini', '[jellyfin]\nplayer = hc\n[new_section]\nnew = yes\n')
                z.writestr('custom.ini', 'replacement')
                z.writestr('.instances/a/trakt_token.json', 'replacement')
            install_archive(archive, root, config)
            self.assertEqual(config.read_text(), '[jellyfin]\nplayer = be\n')
            self.assertEqual(custom.read_text(), 'my custom config')
            self.assertEqual(state.read_text(), 'my token')
            self.assertEqual((root / 'main.py').read_text(), 'new code')
            self.assertIn('[new_section]', (root / 'config-diff.ini').read_text())
            with zipfile.ZipFile(archive, 'a') as z:
                z.writestr('../escape.py', 'bad')
                z.writestr('README.md', 'must not install')
            with self.assertRaises(ValueError):
                install_archive(archive, root, config)
            self.assertFalse((root / 'README.md').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
