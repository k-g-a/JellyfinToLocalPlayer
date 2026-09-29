class EmbyApiThin:
    def __init__(self, data=None, *, host='', api_key='', user_id='', server='emby'):
        from utils.net_tools import requests_urllib

        self.req = requests_urllib
        if not data and not all([host, api_key, user_id]):
            raise ValueError('EmbyApiThin: data or host api_key required')
        self.host = host.rstrip('/').split('/web/index')[0]
        self.api_key = api_key
        self.user_id = user_id
        self.server = server.lower()
        if data:
            self.host = f"{data['scheme']}://{data['netloc']}"
            self.api_key = data['api_key']
            self.user_id = data.get('user_id', '')
            self.server = data.get('server', 'emby').lower()
        self.api_prefix = '/emby' if self.server == 'emby' else ''
        self.headers = {
            'Referer': f'{self.host}/web/index.html',
            'X-Emby-Authorization': f'MediaBrowser Client="embyToLocalPlayer",Token="{self.api_key}"',
            'Authorization': f'MediaBrowser Client="embyToLocalPlayer",Token="{self.api_key}"',
        }

    def api_url(self, path):
        return f'{self.host}{self.api_prefix}/{path.lstrip("/")}'

    def get(self, path, params=None, get_json=True, timeout=5):
        params = params or {'X-Emby-Token': self.api_key}
        params.update(
            {
                'X-Emby-Token': self.api_key,
                'Authorization': f'MediaBrowser Client="EmbyApi",Token="{self.api_key}"',
            }
        )
        url = self.api_url(path)
        res = self.req(url, params=params, get_json=get_json, headers=self.headers, timeout=timeout)
        return res

    def get_playback_info(self, item_id, timeout=15):
        # For emby strm, media info can be scanned out during reporting; this should be the result produced by this request.
        res = self.get(f'Items/{item_id}/PlaybackInfo', timeout=timeout)
        return res

    def get_resume_items(self):
        params = {
            'Fields': 'MediaStreams,PremiereDate,Path',
            'MediaTypes': 'Video',
            'Limit': '12',
        }
        res = self.get(f'Users/{self.user_id}/Items/Resume', params=params)
        return res
