"""Shared Jellyfin metadata helpers for Trakt and Simkl reporting."""
from code.configs import configs, MyLogger

logger = MyLogger()


def get_jellyfin_season_watched_ep_key(jellyfin, eps_data, get_date=False, full_data=False):
    if not jellyfin.user_id:
        api = configs.get_server_api_by_ini(specify_host=jellyfin.host)
        user_id = getattr(api, 'user_id', '')
        if not user_id:
            logger.info('Reporting requires a Jellyfin user_id')
            return
        jellyfin.user_id = user_id
    from code.jellyfin_api import JellyfinApi
    jellyfin: JellyfinApi
    first_ep = eps_data[0]
    ser_id, sea_id = first_ep.get('SeriesId'), first_ep.get('SeasonId')
    if not sea_id:
        return
    try:
        eps_data = jellyfin.get_episodes(item_id=ser_id, season_id=sea_id, get_user_data=True, get_sources=True)['Items']
    except ValueError as e:
        logger.error(f'skip get_jellyfin_season_watched_ep_key: {str(e)[:50]}')
        return
    watched = []
    dates = []
    f_data = []
    for ep in eps_data:
        if not ep['UserData']['Played']:
            continue
        ep_num, sea_num = ep.get('IndexNumber'), ep.get('ParentIndexNumber')
        if not all([ep_num, sea_num]):
            continue
        key = f'{sea_num}-{ep_num}'
        if get_date:
            dates.append(ep.get('PremiereDate'))
        if full_data:
            f_data.append(ep)
        watched.append(key)
    if full_data:
        return watched, dates, f_data
    return (watched, dates) if get_date else watched


def jellyfin_api_via_first_ep(first_ep):
    from code.jellyfin_api import JellyfinApi
    jellyfin = JellyfinApi(host=f"{first_ep['scheme']}://{first_ep['netloc']}",
                   api_key=first_ep['api_key'],
                   user_id=first_ep['user_id'],
                   http_proxy=configs.script_proxy,
                   cert_verify=(not configs.raw.getboolean('dev', 'skip_certificate_verify', fallback=False))
                   )
    return jellyfin
