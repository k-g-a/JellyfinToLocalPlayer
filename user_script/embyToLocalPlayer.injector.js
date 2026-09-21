// Jellyfin JavaScript Injector integration for embyToLocalPlayer.
// Adds explicit local-player actions without replacing Jellyfin playback or browser APIs.
'use strict';
/* global ApiClient */

(() => {
    'use strict';

    const STYLE_ID = 'etlp-injector-style';
    const BUTTON_CLASS = 'etlp-player-button';
    // Edit only these local settings when using different instance ports.
    // Missing settings retain the defaults below; an empty endpoints array disables discovery.
    const SETTINGS = {};
    // false streams through Jellyfin; true translates Jellyfin paths through [src]/[dst].
    const MOUNT_DISK_ENABLE = false;
    const endpoints = [...new Set(SETTINGS.endpoints ?? [
        'http://127.0.0.1:58000',
        'http://127.0.0.1:58001',
    ])].map(url => ({ url: url.replace(/\/$/, ''), available: false, title: '' }));
    const PROBE_INTERVAL_AVAILABLE_MS = SETTINGS.probeIntervalAvailableMs ?? 5000;
    const PROBE_INTERVAL_UNAVAILABLE_MS = SETTINGS.probeIntervalUnavailableMs ?? 10000;
    const REQUEST_TIMEOUT_MS = SETTINGS.requestTimeoutMs ?? 5000;

    if (document.getElementById(STYLE_ID)) {
        return;
    }

    const nativeFetch = window.fetch.bind(window);
    const state = {
        busy: false,
        syncTimer: null,
    };

    function installStyles() {
        const style = document.createElement('style');
        style.id = STYLE_ID;
        style.textContent = `
            .${BUTTON_CLASS} {
                align-items: center;
                border: 0;
                border-radius: 0.45em;
                box-sizing: border-box;
                color: inherit;
                cursor: pointer;
                display: inline-flex;
                gap: 0.4em;
                justify-content: center;
                margin: 0 0.15em;
                min-height: 2.75em;
                padding: 0.55em 0.8em;
                white-space: nowrap;
            }

            .${BUTTON_CLASS}:hover {
                background: rgba(255, 255, 255, 0.14);
            }

            .${BUTTON_CLASS}:focus-visible {
                outline: 0.16em solid currentColor;
                outline-offset: 0.12em;
            }

            .${BUTTON_CLASS}:disabled {
                cursor: progress;
                opacity: 0.55;
            }

            .${BUTTON_CLASS} .etlp-player-button-icon {
                font-size: 1.65em;
            }

            .${BUTTON_CLASS} .etlp-player-button-label {
                font-size: 0.92em;
                font-weight: 600;
                line-height: 1;
            }

            .etlp-toast {
                align-items: center;
                animation: etlp-toast-in 160ms ease-out;
                background: rgba(20, 20, 20, 0.96);
                border-left: 0.3em solid #00a4dc;
                border-radius: 0.35em;
                bottom: 2em;
                box-shadow: 0 0.4em 1.5em rgba(0, 0, 0, 0.35);
                color: #fff;
                display: flex;
                font-family: inherit;
                gap: 0.65em;
                max-width: min(32em, calc(100vw - 4em));
                padding: 0.85em 1em;
                position: fixed;
                right: 2em;
                z-index: 999999;
            }

            .etlp-toast.etlp-toast-error {
                border-left-color: #d32f2f;
            }

            @keyframes etlp-toast-in {
                from { opacity: 0; transform: translateY(0.5em); }
                to { opacity: 1; transform: translateY(0); }
            }
        `;
        document.head.appendChild(style);
    }

    function withTimeout(timeoutMs) {
        const controller = new AbortController();
        const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
        return {
            signal: controller.signal,
            cancel: () => window.clearTimeout(timeoutId),
        };
    }

    function showToast(message, isError = false) {
        document.querySelector('.etlp-toast')?.remove();

        const toast = document.createElement('div');
        toast.className = `etlp-toast${isError ? ' etlp-toast-error' : ''}`;

        const icon = document.createElement('span');
        icon.className = `material-icons ${isError ? 'error_outline' : 'play_arrow'}`;
        icon.setAttribute('aria-hidden', 'true');

        const text = document.createElement('span');
        text.textContent = message;

        toast.append(icon, text);
        document.body.appendChild(toast);
        window.setTimeout(() => toast.remove(), isError ? 6000 : 3000);
    }

    function getApiClient() {
        return typeof ApiClient === 'undefined' ? null : ApiClient;
    }

    function callApiClient(apiClient, method, fallbackProperty) {
        if (typeof apiClient?.[method] === 'function') {
            return apiClient[method]();
        }
        return apiClient?.[fallbackProperty];
    }

    function getRouteItemId() {
        const locations = [window.location.hash, window.location.search];

        for (const locationPart of locations) {
            const queryIndex = locationPart.indexOf('?');
            if (queryIndex === -1) {
                continue;
            }

            const itemId = new URLSearchParams(locationPart.slice(queryIndex + 1)).get('id');
            if (itemId) {
                return itemId;
            }
        }

        return window.location.pathname.match(/\/(?:details|item)\/([a-zA-Z0-9-]+)/)?.[1] || null;
    }

    function isVisible(element) {
        return Boolean(element && !element.hidden && element.getClientRects().length);
    }

    function findNativePlayButton() {
        const candidates = document.querySelectorAll([
            '.itemDetailPage .btnPlay:not(.hide)',
            '.itemDetailPage .btnPlayOrResume',
        ].join(','));
        return Array.from(candidates).find(isVisible) || null;
    }

    function getTrackSelection(nativePlayButton) {
        const page = nativePlayButton.closest('.itemDetailPage') || document;
        const value = selector => page.querySelector(selector)?.value;
        const numberValue = selector => {
            const selectedValue = value(selector);
            return selectedValue === undefined || selectedValue === '' ? null : Number(selectedValue);
        };

        return {
            mediaSourceId: value('.selectSource') || null,
            audioStreamIndex: numberValue('.selectAudio'),
            subtitleStreamIndex: numberValue('.selectSubtitles'),
        };
    }

    function setButtonsBusy(isBusy) {
        state.busy = isBusy;
        document.querySelectorAll(`.${BUTTON_CLASS}`).forEach(button => {
            button.disabled = isBusy;
            button.setAttribute('aria-busy', String(isBusy));
        });
    }

    function removeButtons() {
        document.querySelectorAll(`.${BUTTON_CLASS}`).forEach(button => button.remove());
    }

    function createPlayerButton(endpoint, itemId) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `button-flat ${BUTTON_CLASS}`;
        button.dataset.etlpEndpoint = endpoint.url;
        button.disabled = state.busy;
        button.setAttribute('aria-busy', String(state.busy));
        button.dataset.etlpItemId = itemId;
        button.title = `Play in ${endpoint.title}`;
        button.setAttribute('aria-label', `Play in ${endpoint.title}`);

        const icon = document.createElement('span');
        icon.className = 'material-icons etlp-player-button-icon play_arrow';
        icon.setAttribute('aria-hidden', 'true');

        const label = document.createElement('span');
        label.className = 'etlp-player-button-label';
        label.textContent = `Play in ${endpoint.title}`;

        button.append(icon, label);
        button.addEventListener('click', event => {
            event.preventDefault();
            event.stopPropagation();
            launchPlayer(endpoint, button).catch(error => {
                console.error('[ETLP] Unable to start local playback:', error);
                showToast(error.message || 'Unable to start local playback.', true);
            });
        });
        return button;
    }

    function syncButtons() {
        if (!endpoints.some(endpoint => endpoint.available)) {
            removeButtons();
            return;
        }

        const itemId = getRouteItemId();
        const nativePlayButton = findNativePlayButton();
        if (!itemId || !nativePlayButton) {
            removeButtons();
            return;
        }

        const existingButtons = Array.from(document.querySelectorAll(`.${BUTTON_CLASS}`));
        const expectedEndpoints = endpoints.filter(endpoint => endpoint.available);
        const isCurrent = existingButtons.length === expectedEndpoints.length
            && existingButtons.every(button => button.dataset.etlpItemId === itemId)
            && existingButtons.every(button => button.parentElement === nativePlayButton.parentElement)
            && expectedEndpoints.every(endpoint => existingButtons.some(button =>
                button.dataset.etlpEndpoint === endpoint.url && button.title === `Play in ${endpoint.title}`));

        if (isCurrent) {
            return;
        }

        removeButtons();
        const fragment = document.createDocumentFragment();
        expectedEndpoints.forEach(endpoint => fragment.appendChild(createPlayerButton(endpoint, itemId)));
        nativePlayButton.after(fragment);
    }

    function scheduleButtonSync() {
        window.clearTimeout(state.syncTimer);
        state.syncTimer = window.setTimeout(syncButtons, 80);
    }

    async function probeBackend(endpoint) {
        const timeout = withTimeout(REQUEST_TIMEOUT_MS);
        try {
            const response = await nativeFetch(`${endpoint.url}/etlp/status`, {
                cache: 'no-store',
                headers: { Accept: 'application/json' },
                signal: timeout.signal,
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const status = await response.json();
            endpoint.available = status.service === 'JellyfinToLocalPlayer' && status.ready === true;
            endpoint.title = String(status.title || status.player || 'local player');
        } catch (_error) {
            endpoint.available = false;
        } finally {
            timeout.cancel();
            syncButtons();
            window.setTimeout(
                () => probeBackend(endpoint),
                endpoint.available ? PROBE_INTERVAL_AVAILABLE_MS : PROBE_INTERVAL_UNAVAILABLE_MS,
            );
        }
    }

    async function getPlayableItem(apiClient, pageItemId, mediaSourceId, userId) {
        if (mediaSourceId && mediaSourceId !== pageItemId) {
            try {
                return await apiClient.getItem(userId, mediaSourceId);
            } catch (_error) {
                // Some servers use a media-source id that is not itself an item id.
            }
        }
        return apiClient.getItem(userId, pageItemId);
    }

    async function getEpisodes(apiClient, item, userId) {
        if (item.Type !== 'Episode' || !item.SeriesId || !item.SeasonId) {
            return [];
        }

        try {
            const response = await apiClient.getEpisodes(item.SeriesId, {
                Fields: 'MediaSources,Path,ProviderIds,Chapters',
                SeasonId: item.SeasonId,
                UserId: userId,
            });
            return response?.Items || [];
        } catch (error) {
            console.warn('[ETLP] Episode-list lookup failed; continuing without playlist metadata.', error);
            return [];
        }
    }

    function createPlaybackRequest(apiClient, item, playbackData, episodesInfo, trackSelection) {
        const serverAddress = callApiClient(apiClient, 'serverAddress', '_serverAddress') || window.location.origin;
        const userId = callApiClient(apiClient, 'getCurrentUserId', '_currentUserId')
            || apiClient._serverInfo?.UserId;
        const deviceId = callApiClient(apiClient, 'deviceId', '_deviceId');
        const accessToken = callApiClient(apiClient, 'accessToken', '_accessToken')
            || apiClient._userAuthInfo?.AccessToken
            || apiClient._serverInfo?.AccessToken;
        const serverVersion = apiClient._serverVersion || apiClient._serverInfo?.Version || '12.0.0';

        if (!userId || !deviceId || !accessToken) {
            throw new Error('Jellyfin authentication data is unavailable. Reload the page and sign in again.');
        }

        const startTimeTicks = item.UserData?.PlaybackPositionTicks || 0;
        const query = new URLSearchParams({
            'X-Emby-Device-Id': deviceId,
            'X-Emby-Token': accessToken,
            UserId: userId,
            StartTimeTicks: String(startTimeTicks),
            IsPlayback: 'true',
        });

        if (trackSelection.mediaSourceId) {
            query.set('MediaSourceId', trackSelection.mediaSourceId);
        }
        if (trackSelection.audioStreamIndex !== null) {
            query.set('AudioStreamIndex', String(trackSelection.audioStreamIndex));
        }
        if (trackSelection.subtitleStreamIndex !== null) {
            query.set('SubtitleStreamIndex', String(trackSelection.subtitleStreamIndex));
        }

        const playbackUrl = `${serverAddress.replace(/\/$/, '')}/Items/${item.Id}/PlaybackInfo?${query}`;
        const authorization = [
            `MediaBrowser Client="${apiClient._appName || 'Jellyfin Web'}"`,
            `Device="${apiClient._deviceName || 'Browser'}"`,
            `DeviceId="${deviceId}"`,
            `Version="${apiClient._appVersion || ''}"`,
            `Token="${accessToken}"`,
        ].join(', ');

        return {
            ApiClient: {
                _serverAddress: serverAddress,
                _serverVersion: serverVersion,
            },
            playbackData,
            playbackUrl,
            request: {
                headers: {
                    Authorization: authorization,
                    'X-Emby-Device-Id': deviceId,
                    'X-Emby-Token': accessToken,
                },
            },
            mountDiskEnable: String(MOUNT_DISK_ENABLE),
            extraData: {
                mainEpInfo: item,
                episodesInfo,
                playlistInfo: [],
                serverName: 'jellyfin',
                injectorVersion: '3.0.0',
                userAgent: navigator.userAgent,
            },
        };
    }

    async function launchPlayer(endpoint, button) {
        if (state.busy) return;
        if (!endpoint.available) {
            throw new Error('This local ETLP instance is not available.');
        }

        const apiClient = getApiClient();
        const pageItemId = getRouteItemId();
        const nativePlayButton = findNativePlayButton();
        if (!apiClient || !pageItemId || !nativePlayButton) {
            throw new Error('Jellyfin item data is not ready yet.');
        }

        setButtonsBusy(true);
        try {
            const userId = callApiClient(apiClient, 'getCurrentUserId', '_currentUserId')
                || apiClient._serverInfo?.UserId;
            const trackSelection = getTrackSelection(nativePlayButton);
            const item = await getPlayableItem(apiClient, pageItemId, trackSelection.mediaSourceId, userId);

            if (!['Movie', 'Episode', 'Video', 'MusicVideo'].includes(item.Type)) {
                throw new Error(`ETLP playback is not available for Jellyfin item type “${item.Type}”.`);
            }

            const playbackOptions = {
                UserId: userId,
                StartTimeTicks: item.UserData?.PlaybackPositionTicks || 0,
            };
            if (trackSelection.mediaSourceId) {
                playbackOptions.MediaSourceId = trackSelection.mediaSourceId;
            }

            const [playbackData, episodesInfo] = await Promise.all([
                apiClient.getPlaybackInfo(item.Id, playbackOptions),
                getEpisodes(apiClient, item, userId),
            ]);

            if (!playbackData?.MediaSources?.length || !playbackData.PlaySessionId) {
                throw new Error('Jellyfin did not return usable playback information.');
            }

            const payload = createPlaybackRequest(
                apiClient,
                item,
                playbackData,
                episodesInfo,
                trackSelection,
            );
            const timeout = withTimeout(REQUEST_TIMEOUT_MS);
            try {
                const response = await nativeFetch(`${endpoint.url}/embyToLocalPlayer/`, {
                    method: 'POST',
                    body: JSON.stringify(payload),
                    signal: timeout.signal,
                });
                if (!response.ok) {
                    const result = await response.json().catch(() => ({}));
                    throw new Error(result.error || `ETLP backend returned HTTP ${response.status}.`);
                }
            } finally {
                timeout.cancel();
            }

            showToast(`Opening “${item.Name || 'video'}” with ${endpoint.title}.`);
        } finally {
            setButtonsBusy(false);
            button.blur();
        }
    }

    installStyles();

    const observer = new MutationObserver(scheduleButtonSync);
    observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['class'],
        childList: true,
        subtree: true,
    });
    window.addEventListener('hashchange', scheduleButtonSync);
    window.addEventListener('popstate', scheduleButtonSync);
    endpoints.forEach(probeBackend);
})();
