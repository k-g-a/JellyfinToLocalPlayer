// ==UserScript==
// @name         embyToLocalPlayer
// @name:zh-CN   embyToLocalPlayer
// @name:en      embyToLocalPlayer
// @namespace    https://github.com/kjtsune/embyToLocalPlayer
// @version      2026.02.11
// @description  Emby/Jellyfin: play in an external local player and report playback progress back. Supports Plex.
// @description:zh-CN Emby/Jellyfin 调用外部本地播放器，并回传播放记录。适配 Plex。
// @description:en  Play in an external player. Update watch history to Emby/Jellyfin server. Support Plex.
// @author       Kjtsune
// @match        *://*/web/index.html*
// @match        *://*/*/web/index.html*
// @match        *://*/web/
// @match        *://*/*/web/
// @match        https://app.emby.media/*
// @match        https://app.plex.tv/*
// @icon         https://www.google.com/s2/favicons?sz=64&domain=emby.media
// @grant        unsafeWindow
// @grant        GM_info
// @grant        GM_xmlhttpRequest
// @grant        GM_registerMenuCommand
// @grant        GM_unregisterMenuCommand
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_deleteValue
// @run-at       document-start
// @connect      127.0.0.1
// @license MIT
// ==/UserScript==
'use strict';
/*global ApiClient*/

(function () {
    'use strict';
    let fistTime = true;
    let config = {
        logLevel: 2,
        disableOpenFolder: undefined, // Change undefined to true to disable the open folder button.
        crackFullPath: undefined,
        disableForLiveTv: undefined, // Change undefined to true to play IPTV in the browser.
        enableResumeReorder: true, // Change true to undefined to disable. Keeps the first 2 Continue Watching items, moves the rest updated within the last 3 days forward.
        resumeHideSomeSeries: undefined, // Change undefined to true to enable the userscript menu for hiding specific TV series.
    };

    let etlpStorageKeys = {
        webPlayerEnable: 'webPlayerEnable',
        mountDiskEnable: 'mountDiskEnable',
        crackFullPath: 'etlpCrackFullPath',
        resumeHide: 'etlpResumeHideSomeSeries',
        cacheResumeIds: 'etlpCacheResumeIds',
        hideSeriesIds: 'etlpResumeHideSeriesIds',
    }

    const originFetch = fetch;

    let logger = {
        error: function (...args) {
            if (config.logLevel >= 1) {
                console.log('%cERROR', 'color: #fff; background: #d32f2f; font-weight: bold; padding: 2px 6px; border-radius: 3px;', ...args);
            }
        },
        info: function (...args) {
            if (config.logLevel >= 2) {
                console.log('%cINFO', 'color: #fff; background: #1976d2; font-weight: bold; padding: 2px 6px; border-radius: 3px;', ...args);
            }
        },
        debug: function (...args) {
            if (config.logLevel >= 3) {
                console.log('%cDEBUG', 'color: #333; background: #ffeb3b; font-weight: bold; padding: 2px 6px; border-radius: 3px;', ...args);
            }
        },
    };

    function myBool(value) {
        if (Array.isArray(value) && value.length === 0) return false;
        if (value !== null && typeof value === 'object' && Object.keys(value).length === 0) return false;
        return Boolean(value);
    }

    async function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    function isHidden(el) {
        return (el.offsetParent === null);
    }

    function getVisibleElement(elList) {
        if (!elList) return;
        if (Object.prototype.isPrototypeOf.call(NodeList.prototype, elList)) {
            for (let i = 0; i < elList.length; i++) {
                if (!isHidden(elList[i])) {
                    return elList[i];
                }
            }
        } else {
            return elList;
        }
    }

    function overwriteConfByStore() {
        function overwriteByKey(confKey) {
            let confLocal = localStorage.getItem(confKey);
            if (confLocal == null) return;
            if (confLocal == 'true') {
                GM_setValue(confKey, true);

            } else if (confLocal == 'false') {
                GM_setValue(confKey, false);
            }
            let confGM = GM_getValue(confKey, null);
            if (confGM !== null) {
                // Note: etlpResumeHideSomeSeries is converted to resumeHideSomeSeries.
                let _confKey = confKey.replace(/^etlp/, '');
                _confKey = _confKey.charAt(0).toLowerCase() + _confKey.slice(1);
                config[_confKey] = confGM;
            };
        }
        overwriteByKey(etlpStorageKeys.crackFullPath);
        overwriteByKey(etlpStorageKeys.resumeHide);
    }

    function playNotifiy(title = 'Now Playing', subtitle = 'Enjoy your content') {
        if (!document.getElementById('play-notification-style')) {
            const style = document.createElement('style');
            style.id = 'play-notification-style';
            style.textContent = `
                @keyframes slideIn { from { transform: translateX(400px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
                @keyframes slideOut { from { transform: translateX(0); opacity: 1; } to { transform: translateX(400px); opacity: 0; } }
                @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
            `;
            document.head.appendChild(style);
        }

        const notification = document.createElement('div');
        notification.innerHTML = `
            <svg width="40" height="40" viewBox="0 0 24 24" style="animation: pulse 1.5s ease-in-out infinite; flex-shrink: 0;">
                <circle cx="12" cy="12" r="10" stroke="white" stroke-width="2" fill="none" opacity="0.3"/>
                <path d="M9 8L17 12L9 16V8Z" fill="white"/>
            </svg>
            <div>
                <div style="font-weight: 600; font-size: 16px;">${title}</div>
                <div style="font-size: 13px; opacity: 0.9;">${subtitle}</div>
            </div>
        `;

        notification.style.cssText = `
            position: fixed; bottom: 30px; right: 30px; z-index: 999999;
            background: linear-gradient(135deg, #0296beff 0%, #008a51ff 100%);
            border-radius: 12px; padding: 20px 25px; color: white;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            display: flex; align-items: center; gap: 15px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            animation: slideIn 0.5s ease-out;
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOut 0.5s ease-in';
            setTimeout(() => notification.remove(), 500);
        }, 3000);
    }

    let menuRegistry = [];
    let registeredMenus = [];

    function switchLocalStorage(key, defaultValue = 'true', trueValue = 'true', falseValue = 'false') {
        if (key in localStorage) {
            let value = (localStorage.getItem(key) === trueValue) ? falseValue : trueValue;
            localStorage.setItem(key, value);
        } else {
            localStorage.setItem(key, defaultValue);
        }
        logger.info('switchLocalStorage', key, 'to', localStorage.getItem(key));
    }

    function registerAllMenus() {
        registeredMenus.forEach(id => GM_unregisterMenuCommand(id));
        registeredMenus = [];

        menuRegistry.forEach(item => {
            let id;

            if (item.type === 'switch') {
                let title = item.menuStart + item.switchNameMap[localStorage.getItem(item.storageKey)] + item.menuEnd;
                id = GM_registerMenuCommand(title, () => {
                    switchLocalStorage(item.storageKey);
                    registerAllMenus(); // Refresh menu display
                });
            } else if (item.type === 'callback') {
                id = GM_registerMenuCommand(item.title, item.callback);
            }

            registeredMenus.push(id);
            item.menuId = id;
        });
    }

    function setModeSwitchMenu(storageKey, menuStart = '', menuEnd = '', defaultValue = 'Off', trueValue = 'On', falseValue = 'Off') {
        let switchNameMap = { 'true': trueValue, 'false': falseValue, null: defaultValue };

        menuRegistry.push({
            type: 'switch',
            storageKey,
            menuStart,
            menuEnd,
            switchNameMap
        });

        registerAllMenus();
    }

    function setCallbackMenu(title, callback) {
        menuRegistry.push({
            type: 'callback',
            title,
            callback
        });

        registerAllMenus();
    }

    function hideCurrentSeries() {
        const urlMatch = window.location.href.match(/id=(\d+)/);
        let hint = 'Please perform this action on the root item page of the TV series you want to hide';
        if (!urlMatch) {
            alert(hint);
            return;
        }

        const seriesId = urlMatch[1];
        if (!seriesId) {
            alert(hint);
            return;
        }

        let hideList = [];
        const stored = localStorage.getItem(etlpStorageKeys.hideSeriesIds);
        if (stored) {
            try {
                hideList = JSON.parse(stored);
            } catch (e) {
                logger.error('Failed to parse hide list:', e);
                hideList = [];
            }
        }

        if (!hideList.includes(seriesId)) {
            hideList.push(seriesId);
            localStorage.setItem(etlpStorageKeys.hideSeriesIds, JSON.stringify(hideList));
            logger.info('Hidden TV series, SeriesId:', seriesId);
            alert(`This TV series has been hidden. Note: this must be done on the series main item page. SeriesId=${seriesId}`);
        } else {
            alert('This TV series is already in the hide list');
        }
    }

    function resetHiddenSeries() {
        localStorage.removeItem(etlpStorageKeys.hideSeriesIds);
        logger.info('Hide settings have been reset');
        alert('Hide settings have been reset, takes effect after refreshing the page');
    }

    function removeErrorWindows() {
        let okButtonList = document.querySelectorAll('button[data-id="ok"]');
        let state = false;
        for (let index = 0; index < okButtonList.length; index++) {
            const element = okButtonList[index];
            if (element.textContent.search(/.+/) != -1) {
                element.click();
                if (isHidden(element)) { continue; }
                state = true;
            }
        }

        let jellyfinSpinner = document.querySelector('div.docspinner');
        if (jellyfinSpinner) {
            jellyfinSpinner.remove();
            state = true;
        };

        let plexErrorSelector = '[class*="Modal-small"] [class*="ModalContent-modalContent"] [class*="PlayerErrorModal-modalHeader"]';
        if (document.querySelector(plexErrorSelector)) {
            let escEvent = new KeyboardEvent('keydown', {
                key: 'Escape',
                keyCode: 27,
                code: 'Escape',
                which: 27,
                bubbles: true,
            });
            document.dispatchEvent(escEvent);
            state = true;
        }

        return state;
    }

    async function removeErrorWindowsMultiTimes() {
        for (const times of Array(15).keys()) {
            await sleep(200);
            if (removeErrorWindows()) {
                logger.info(`remove error window used time: ${(times + 1) * 0.2}`);
                break;
            };
        }
    }

    function sendDataToLocalServer(data, path) {
        let url = `http://127.0.0.1:58000/${path}/`;
        GM_xmlhttpRequest({
            method: 'POST',
            url: url,
            data: JSON.stringify(data),
            headers: {
                'Content-Type': 'application/json'
            },
            onerror: function (error) {
                alert(`${url}\nRequest error: the local server is not running. Please check the usage instructions.\nhttps://github.com/kjtsune/embyToLocalPlayer`);
                console.error('Request error:', error);
            }
        });
        logger.info(path, data);
    }

    let serverName = null;

    function detectServerName() {
        if (serverName === null && typeof ApiClient !== 'undefined') {
            let appName = ApiClient._appName || ApiClient._serverInfo?.ProductName;
            serverName = appName ? appName.split(' ')[0].toLowerCase() : null;
        }
        return serverName;
    }

    function getApiUrl(path) {
        let serverAddress = ApiClient._serverAddress || window.location.origin;
        let apiPrefix = detectServerName() === 'emby' ? '/emby' : '';
        return `${serverAddress.replace(/\/$/, '')}${apiPrefix}/${path.replace(/^\//, '')}`;
    }

    let episodesInfoCache = []; // ['type:[Episodes|NextUp|Items]', resp]
    let episodesInfoRe = /\/Episodes\?IsVirtual|\/NextUp\?Series|\/Items\?ParentId=\w+&Filters=IsNotFolder&Recursive=true/; // Items already excludes playlists
    // Click location: Episodes = Continue Watching; if it is Up Next, it may only contain one episode's info | NextUp = new playback or library playback | Items = season playback. Only Episodes returns data for all episodes.
    let playlistInfoCache = null;
    let resumeRawInfoCache = null;
    let resumePlaybackCache = {};
    let resumeItemDataCache = {};
    let allPlaybackCache = {};
    let allItemDataCache = {};
    let episodesWithPathCache = {};

    let metadataChangeRe = /\/MetadataEditor|\/Refresh\?/;
    let metadataMayChange = false;

    function cleanOptionalCache() {
        resumeRawInfoCache = null;
        resumePlaybackCache = {};
        resumeItemDataCache = {};
        allPlaybackCache = {};
        allItemDataCache = {};
        episodesInfoCache = [];
        episodesWithPathCache = {};
    }

    function throttle(fn, delay) {
        let lastTime = 0;
        return function (...args) {
            const now = Date.now();
            if (now - lastTime >= delay) {
                lastTime = now;
                fn.apply(this, args);
            }
        };
    }

    let addOpenFolderElement = throttle(_addOpenFolderElement, 100);

    async function _addOpenFolderElement(itemId) {
        if (config.disableOpenFolder) return;
        let mediaSources = null;
        for (const _ of Array(5).keys()) {
            await sleep(500);
            mediaSources = getVisibleElement(document.querySelectorAll('div.mediaSources'));
            if (mediaSources) break;
        }
        if (!mediaSources) return;
        let pathDiv = mediaSources.querySelector('div[class^="sectionTitle sectionTitle-cards"] > div');
        if (!pathDiv || pathDiv.className == 'mediaInfoItems' || pathDiv.id == 'addFileNameElement') return;
        let full_path = pathDiv.textContent;
        if (!full_path.match(/[\\/:]/)) return;
        if (full_path.match(/\d{1,3}\.?\d{0,2} (MB|GB)/)) return;

        let itemData = (itemId in allItemDataCache) ? allItemDataCache[itemId] : null
        let strmFile = (full_path.startsWith('http')) ? itemData?.Path : null

        let openButtonHtml = `<a id="openFolderButton" is="emby-linkbutton" class="raised item-tag-button 
        nobackdropfilter emby-button" ><i class="md-icon button-icon button-icon-left">link</i>Open Folder</a>`
        pathDiv.insertAdjacentHTML('beforebegin', openButtonHtml);
        let btn = mediaSources.querySelector('a#openFolderButton');
        if (strmFile) {
            pathDiv.innerHTML = pathDiv.innerHTML + '<br>' + strmFile;
            full_path = strmFile; // emby displays the link inside the strm as the path
        }
        btn.addEventListener('click', () => {
            logger.info(full_path);
            sendDataToLocalServer({ full_path: full_path }, 'openFolder');
        });
    }

    async function addFileNameElement(resp) {
        let mediaSources = null;
        for (const _ of Array(5).keys()) {
            await sleep(500);
            mediaSources = getVisibleElement(document.querySelectorAll('div.mediaSources'));
            if (mediaSources) break;
        }
        if (!mediaSources) return;
        let pathDivs = mediaSources.querySelectorAll('div[class^="sectionTitle sectionTitle-cards"] > div');
        if (!pathDivs) return;
        pathDivs = Array.from(pathDivs);
        let _pathDiv = pathDivs[0];
        if (_pathDiv.id == 'addFileNameElement') return;
        let isAdmin = !/\d{4}\/\d+\/\d+/.test(_pathDiv.textContent); // Non-admins only have a file type div containing the added date
        let isStrm = _pathDiv.textContent.startsWith('http');
        if (isAdmin) {
            if (!isStrm) { return; }
            pathDivs = pathDivs.filter((_, index) => index % 2 === 0); // For admins, one file has both a path div and a file type div
        }

        let sources = await resp.clone().json();
        sources = sources.MediaSources;
        for (let index = 0; index < pathDivs.length; index++) {
            const pathDiv = pathDivs[index];
            let fileName = sources[index].Name; // With multiple versions, this is the version name.
            let filePath = sources[index].Path;
            let strmFile = filePath.startsWith('http');
            if (!strmFile) {
                fileName = filePath.split('\\').pop().split('/').pop();
                fileName = (config.crackFullPath && !isAdmin) ? filePath : fileName;
            }
            let fileDiv = `<div id="addFileNameElement">${fileName}</div> `
            if (strmFile && (!isAdmin && config.crackFullPath)) {
                fileDiv = `<div id="addFileNameElement">${fileName}<br>${filePath}</div> `
            }
            pathDiv.insertAdjacentHTML('beforebegin', fileDiv);
        }
    }

    function makeItemIdCorrect(itemId) {
        if (serverName !== 'emby') { return itemId; }
        if (!resumeRawInfoCache || !episodesInfoCache) { return itemId; }
        let resumeIds = resumeRawInfoCache.map(item => item.Id);
        if (resumeIds.includes(itemId)) { return itemId; }
        let pageId = window.location.href.match(/\/item\?id=(\d+)/)?.[1];
        if (resumeIds.includes(pageId) && itemId == episodesInfoCache[0].Id) {
            // Fix: when entering an episode detail page from Continue Watching, if it is not the first episode, the first episode's video file info gets requested, causing playback failure.
            // Manual workaround: click play from the episode card below, or re-enter the episode detail page from the episode card and then play.
            // Side effect of this function: clicking play on the first episode card at the bottom of the episode detail page will play the current episode.
            // Workaround for the side effect: click again, or click the first episode card to enter its detail page before playing. Users rarely go back to the first episode anyway.
            return pageId;

        } else if (window.location.href.match(/serverId=/)) {
            return itemId; // Only handle the home page Continue Watching and episode detail pages; ignore other pages.
        }
        let correctSeaId = episodesInfoCache.find(item => item.Id == itemId)?.SeasonId;
        let correctItemId = resumeRawInfoCache.find(item => item.SeasonId == correctSeaId)?.Id;
        if (correctSeaId && correctItemId) {
            logger.info(`makeItemIdCorrect, old=${itemId}, new=${correctItemId}`)
            return correctItemId;
        }
        return itemId;
    }

    async function embyToLocalPlayer(playbackUrl, request, playbackData, extraData) {
        let data = {
            ApiClient: ApiClient,
            playbackData: playbackData,
            playbackUrl: playbackUrl,
            request: request,
            mountDiskEnable: localStorage.getItem(etlpStorageKeys.mountDiskEnable),
            extraData: extraData,
            fistTime: fistTime,
        };
        sendDataToLocalServer(data, 'embyToLocalPlayer');
        removeErrorWindowsMultiTimes();
        fistTime = false;
    }

    async function apiClientGetWithCache(itemId, cacheList, funName) {
        if (!itemId) {
            logger.info(`Skip ${funName} ${itemId}`);
        }
        for (const cache of cacheList) {
            if (itemId in cache) {
                logger.info(`HIT ${funName} itemId=${itemId}`)
                return cache[itemId];
            }
        }
        logger.info(`MISS ${funName} itemId=${itemId}`)
        let resInfo;
        switch (funName) {
            case 'getPlaybackInfo':
                resInfo = await ApiClient.getPlaybackInfo(itemId);
                break;
            case 'getItem':
                resInfo = await ApiClient.getItem(ApiClient._serverInfo.UserId, itemId);
                break;
            case 'getEpisodes':
                {
                    let seasonId = itemId;
                    let options = {
                        'Fields': 'MediaSources,Path,ProviderIds',
                        'SeasonId': seasonId,
                    }
                    resInfo = await ApiClient.getEpisodes(seasonId, options);
                    break;
                }
            default:
                break;
        }
        for (const cache of cacheList) {
            if (funName == 'getPlaybackInfo') {
                // The external subtitle index changes before and after strm ffprobe processing, so do not cache.
                let runtime = resInfo?.MediaSources?.[0]?.RunTimeTicks;
                if (!runtime)
                    break;
            }
            cache[itemId] = resInfo;
        }
        return resInfo;
    }

    async function getPlaybackWithCace(itemId) {
        return apiClientGetWithCache(itemId, [resumePlaybackCache, allPlaybackCache], 'getPlaybackInfo');
    }

    async function getItemInfoWithCace(itemId) {
        return apiClientGetWithCache(itemId, [resumeItemDataCache, allItemDataCache], 'getItem');
    }

    async function getEpisodesWithCace(seasonId) {
        return apiClientGetWithCache(seasonId, [episodesWithPathCache], 'getEpisodes');
    }

    async function dealWithPlaybackInfo(raw_url, url, options) {
        console.time('dealWithPlaybackInfo');
        let rawId = url.match(/\/Items\/(\w+)\/PlaybackInfo/)[1];
        episodesInfoCache = episodesInfoCache[0] ? episodesInfoCache[1].clone() : null;
        let itemId = rawId;
        let [playbackData, mainEpInfo, episodesInfoData] = await Promise.all([
            getPlaybackWithCace(itemId), // originFetch(raw_url, request), may throw NoCompatibleStream
            getItemInfoWithCace(itemId),
            episodesInfoCache?.json(),
        ]);
        console.timeEnd('dealWithPlaybackInfo');
        episodesInfoData = (episodesInfoData && episodesInfoData.Items) ? episodesInfoData.Items : null;
        episodesInfoCache = episodesInfoData;
        let correctId = makeItemIdCorrect(itemId);
        url = url.replace(`/${rawId}/`, `/${correctId}/`)
        if (itemId != correctId) {
            itemId = correctId;
            [playbackData, mainEpInfo] = await Promise.all([
                getPlaybackWithCace(itemId),
                getItemInfoWithCace(itemId),
            ]);
            let startPos = mainEpInfo.UserData.PlaybackPositionTicks;
            url = url.replace('StartTimeTicks=0', `StartTimeTicks=${startPos}`);
        }
        let playlistData = (playlistInfoCache && playlistInfoCache.Items) ? playlistInfoCache.Items : null;
        episodesInfoCache = []
        let extraData = {
            mainEpInfo: mainEpInfo,
            episodesInfo: episodesInfoData,
            playlistInfo: playlistData,
            serverName: detectServerName(),
            gmInfo: GM_info,
            userAgent: navigator.userAgent,
        }
        playlistInfoCache = null;
        // resumeInfoCache = null;
        logger.info(extraData);
        if (mainEpInfo?.Type == 'Trailer') {
            alert('etlp: Does not support Trailers plugin. Please disable it.');
            return false;
        }
        if (config.disableForLiveTv && mainEpInfo?.Type == 'TvChannel') { return 'disableForLiveTv'; }
        let notBackdrop = Boolean(playbackData.MediaSources[0].Path.search(/\Wbackdrop/i) == -1);
        if (notBackdrop) {
            let _req = options ? options : raw_url;
            playNotifiy();
            embyToLocalPlayer(url, _req, playbackData, extraData);
            return true;
        }
        return false;
    }

    async function deailWithItemInfo(item) {
        let itemId = item.Id;
        let seasonId = item.SeasonId;

        let [mainEpInfo, playbackData, episodesInfoData] = await Promise.all([
            getItemInfoWithCace(itemId),
            getPlaybackWithCace(itemId),
            (seasonId) ? getEpisodesWithCace(seasonId) : null,
        ]);

        let positonTicks = item.UserData.PlaybackPositionTicks;
        let userId = ApiClient._serverInfo.UserId;
        let deviceId = ApiClient._deviceId;
        let accessToken = ApiClient._userAuthInfo?.AccessToken || ApiClient._serverInfo?.AccessToken;
        if (!accessToken) {
            playNotifiy('Not accessToken');
        }
        let urlParams = {
            'X-Emby-Device-Id': deviceId,
            'StartTimeTicks': positonTicks,
            'X-Emby-Token': accessToken,
            'UserId': userId,
            'IsPlayback': true
        };
        let baseUrl = getApiUrl(`Items/${itemId}/PlaybackInfo`);
        let searchParams = new URLSearchParams(urlParams);
        let playbackUrl = `${baseUrl}?${searchParams.toString()}`;
        let episodesInfo = episodesInfoData?.Items || [];
        let extraData = {
            mainEpInfo: mainEpInfo,
            episodesInfo: episodesInfo,
            playlistInfo: [],
            serverName: detectServerName(),
            gmInfo: GM_info,
            userAgent: navigator.userAgent,
        }
        let requestHeaders = {
            'X-Emby-Token': accessToken,
            'X-Emby-Device-Id': deviceId,
        };
        if (detectServerName() === 'jellyfin') {
            requestHeaders.Authorization = [
                `MediaBrowser Client="${ApiClient._appName || 'Jellyfin Web'}"`,
                `Device="${ApiClient._deviceName || 'Browser'}"`,
                `DeviceId="${deviceId}"`,
                `Version="${ApiClient._appVersion || ''}"`,
                `Token="${accessToken}"`,
            ].join(', ');
        }
        let request = { headers: requestHeaders };
        embyToLocalPlayer(playbackUrl, request, playbackData, extraData)
    }

    document.addEventListener('click', e => {
        if (localStorage.getItem(etlpStorageKeys.webPlayerEnable) == 'true') { return; }
        // if (window.location.hash != '#!/home') { return; }
        const cardPlayBtn = e.target.closest('button.cardOverlayFab-primary[data-action="play"]');
        // Latest TV and library TV will be "resume" and need an extra nextup request to get season/episode info. But multi-version only returns one version, so multi-version info must be requested again before playback.
        // const cardPlayBtn = e.target.closest('button.cardOverlayFab-primary[data-action="play"], button.cardOverlayFab-primary[data-action="resume"]');
        // const listPlayBtn = e.target.closest('button.listItem[data-id="resume"][data-action="custom"]');
        // const listShuffleBtn = e.target.closest('button.listItem[data-id="shuffle"][data-action="custom"]');
        const playButton = cardPlayBtn;

        if (!playButton) {
            return;
        }
        const container = e.target.closest('div[is="emby-itemscontainer"]');
        if (!container || (!container._itemSource && !container.items)) {
            logger.info('🎬 Play button clicked, but not within a recognized item list container.');
            return;
        }
        const parentCard = e.target.closest('.virtualScrollItem.card, .backdropCard[data-index]');
        if (!parentCard) {
            return;
        }

        const index = parentCard._dataItemIndex ?? parentCard.dataset.index;
        const itemList = container._itemSource || container.items;
        const item = itemList[index];
        const action = playButton.dataset.action || playButton.dataset.mode;
        let itemType = item.Type;
        if (!['Movie', 'Episode'].includes(itemType)) {
            logger.info('🎬 Play button clicked, but not within legal itemType.');
            return
        }
        logger.info(`🎬 Action '${action}' triggered for item at index ${index}:`, item);
        e.preventDefault();
        e.stopImmediatePropagation();
        deailWithItemInfo(item);
        let title = item.SeriesName || item.Name;
        let subTitle = item.SeriesName && item.Name || item.ProductionYear;
        playNotifiy(title, subTitle);
    }, true);

    async function cacheResumeItemInfo() {
        let inInit = !myBool(resumeRawInfoCache);
        let resumeIds;
        let storageKey = etlpStorageKeys.cacheResumeIds;
        if (inInit) {
            resumeIds = localStorage.getItem(storageKey)
            if (resumeIds) {
                resumeIds = JSON.parse(resumeIds);
            } else {
                return
            }
        } else {
            resumeIds = resumeRawInfoCache.slice(0, 5).map(item => item.Id);
            let seasonIds = resumeRawInfoCache.slice(0, 5).map(item => item.SeasonId);
            await Promise.all(seasonIds.filter(Boolean).map(sid => getEpisodesWithCace(sid)));
            localStorage.setItem(storageKey, JSON.stringify(resumeIds));
        }

        for (let [globalCache, getFun] of [[resumePlaybackCache, getPlaybackWithCace], [resumeItemDataCache, getItemInfoWithCace]]) {
            let cacheDataAcc = {};
            if (myBool(globalCache)) {
                cacheDataAcc = globalCache;
                resumeIds = resumeIds.filter(id => !(id in globalCache));
                if (resumeIds.length == 0) { return; }
            }
            let itemInfoList = await Promise.all(
                resumeIds.map(id => getFun(id))
            )
            globalCache = itemInfoList.reduce((acc, result, index) => {
                acc[resumeIds[index]] = result;
                return acc;
            }, cacheDataAcc);
        }

    }

    async function cloneAndCacheFetch(resp, key, cache) {
        try {
            const data = await resp.clone().json();
            cache[key] = data;
            return data;
        } catch (_error) {
            // pass
        }
    }

    let itemInfoRe = /\/Items\/(\w+)\?/; // Must be strict, otherwise manually marking as played (PlayedItems) would also match and cache wrong data.

    unsafeWindow.fetch = async (input, options) => {
        let isStrInput = typeof input === 'string';
        let urlStr = isStrInput ? input : input.url;

        if (serverName === null) {
            detectServerName();
        } else {
            if (typeof ApiClient != 'undefined' && ApiClient._deviceName != 'embyToLocalPlayer' && localStorage.getItem(etlpStorageKeys.webPlayerEnable) != 'true') {
                ApiClient._deviceName = 'embyToLocalPlayer'
                cacheResumeItemInfo();
            }
        }
        if (metadataMayChange && urlStr.includes('Items')) {
            if (urlStr.includes('reqformat') && !urlStr.includes('fields')) {
                cleanOptionalCache();
                metadataMayChange = false;
                logger.info('cleanOptionalCache by metadataMayChange')
            }
        }
        // Adapt to playlist and library Play All / Shuffle. This disables version filtering and title beautification.
        if (urlStr.includes('Items?') && /Limit=(300|1000|5\d\d\d)/.test(urlStr)) {
            let _resp = await originFetch(input, options);
            if (serverName == 'emby') {
                await ApiClient._userViewsPromise?.then(result => {
                    let viewsItems = result.Items;
                    let viewsIds = [];
                    viewsItems.forEach(item => {
                        viewsIds.push(item.Id);
                    });
                    let viewsRegex = viewsIds.join('|');
                    viewsRegex = `ParentId=(${viewsRegex})`
                    if (!RegExp(viewsRegex).test(urlStr)) { // Needed for title beautification when clicking season play, not library shuffle.
                        episodesInfoCache = ['Items', _resp.clone()]
                        logger.info('episodesInfoCache', episodesInfoCache);
                        logger.info('viewsRegex', viewsRegex);
                        return _resp;
                    }
                }).catch(error => {
                    console.error('Error occurred: ', error);
                });
            }

            playlistInfoCache = null;
            let _resd = await _resp.clone().json();
            if (!_resd.Items[0]) {
                logger.error('playlist is empty, skip');
                return _resp;
            }
            if (['Movie', 'MusicVideo', 'Episode'].includes(_resd.Items[0].Type)) {
                playlistInfoCache = _resd
                logger.info('playlistInfoCache', playlistInfoCache);
            }
            return _resp
        }
        // Get episode titles etc., only used for title beautification; placed later to avoid mistakenly intercepting home page right-click library shuffle data.
        let _epMatch = urlStr.match(episodesInfoRe);
        if (_epMatch) {
            _epMatch = _epMatch[0].split(['?'])[0].substring(1); // Episodes|NextUp|Items
            let _resp = await originFetch(input, options);
            episodesInfoCache = [_epMatch, _resp.clone()]
            logger.info('episodesInfoCache', episodesInfoCache);
            return _resp
        }

        if (urlStr.includes('Items/Resume') && urlStr.includes('MediaTypes=Video')) {
            let reqUrl = urlStr;

            if (config.enableResumeReorder) {
                reqUrl = urlStr.replace(/Fields=([^&]*)/, 'Fields=$1,DateCreated');
            }

            let fetchInput = isStrInput ? reqUrl : new Request(reqUrl, input);

            let _resp = await originFetch(fetchInput, options);
            let _resd = await _resp.clone().json();

            // Handle hiding specific TV series
            if (config.resumeHideSomeSeries && _resd.Items && _resd.Items.length > 0) {
                const hideListStr = localStorage.getItem(etlpStorageKeys.hideSeriesIds);
                if (hideListStr) {
                    try {
                        const hideList = JSON.parse(hideListStr);
                        const originalLength = _resd.Items.length;
                        _resd.Items = _resd.Items.filter(item => {
                            if (!item.SeriesId) return true;
                            return !hideList.includes(item.SeriesId);
                        });
                        const hiddenCount = originalLength - _resd.Items.length;
                        if (hiddenCount > 0) {
                            logger.info(`Hidden ${hiddenCount} TV series items`);
                        }
                    } catch (e) {
                        logger.error('Failed to parse hide list:', e);
                    }
                }
            }

            if (config.enableResumeReorder && _resd.Items && _resd.Items.length > 2) {
                const now = new Date();
                const threeDaysAgo = new Date(now.getTime() - 3 * 24 * 60 * 60 * 1000);
                const firstTwo = _resd.Items.slice(0, 2);
                const rest = _resd.Items.slice(2);
                const recentItems = [];
                const olderItems = [];
                rest.forEach(item => {
                    const dateCreated = new Date(item.DateCreated);
                    if (dateCreated >= threeDaysAgo) {
                        recentItems.push(item);
                    } else {
                        olderItems.push(item);
                    }
                });
                _resd.Items = [...firstTwo, ...recentItems, ...olderItems];
                logger.info(`Reorder done: first 2 kept, ${recentItems.length} items from the last 3 days moved forward, ${olderItems.length} older items moved back`);
            }

            const modifiedBody = JSON.stringify(_resd);
            const modifiedResponse = new Response(modifiedBody, {
                status: _resp.status,
                statusText: _resp.statusText,
                headers: _resp.headers
            });

            resumeRawInfoCache = _resd.Items;
            cacheResumeItemInfo();
            logger.info('resumeRawInfoCache', resumeRawInfoCache);

            return modifiedResponse;
        }
        // Cache itemInfo; it may also match Items/Resume, so it is placed later.
        if (urlStr.match(itemInfoRe)) {
            let itemId = urlStr.match(itemInfoRe)[1];
            let resp = await originFetch(input, options);
            logger.info(`CACHE allItemDataCache itemId=${itemId}`);
            cloneAndCacheFetch(resp, itemId, allItemDataCache);
            return resp;
        }
        try {
            if (urlStr.indexOf('/PlaybackInfo?UserId') != -1) {
                if (urlStr.indexOf('IsPlayback=true') != -1 && localStorage.getItem(etlpStorageKeys.webPlayerEnable) != 'true') {
                    let dealRes = await dealWithPlaybackInfo(input, urlStr, options);
                    if (dealRes && dealRes != 'disableForLiveTv') { return; }
                } else {
                    let itemId = urlStr.match(/\/Items\/(\w+)\/PlaybackInfo/)[1];
                    let resp = await originFetch(input, options);
                    addFileNameElement(resp.clone()); // itemId data does not contain multi-version file info, so it is not used
                    addOpenFolderElement(itemId);
                    logger.info(`CACHE allPlaybackCache itemId=${itemId}`);
                    cloneAndCacheFetch(resp.clone(), itemId, allPlaybackCache);
                    return resp;
                }
            } else if (urlStr.indexOf('/Playing/Stopped') != -1 && localStorage.getItem(etlpStorageKeys.webPlayerEnable) != 'true') {
                return
            }
        } catch (error) {
            logger.error(error, input, urlStr);
            removeErrorWindowsMultiTimes();
            return
        }

        if (urlStr.match(metadataChangeRe)) {
            if (urlStr.includes('MetadataEditor')) {
                metadataMayChange = true;
            } else {
                cleanOptionalCache();
                logger.info('cleanOptionalCache by Refresh')
            }
        }
        return originFetch(input, options);
    }

    function initXMLHttpRequest() {

        const originOpen = XMLHttpRequest.prototype.open;
        const originSend = XMLHttpRequest.prototype.send;
        const originSetHeader = XMLHttpRequest.prototype.setRequestHeader;

        XMLHttpRequest.prototype.setRequestHeader = function (header, value) {
            this._headers[header] = value;
            return originSetHeader.apply(this, arguments);
        }

        XMLHttpRequest.prototype.open = function (method, url) {
            this._method = method;
            this._url = url;
            this._headers = {};

            if (serverName === null && this._url.indexOf('X-Plex-Product') != -1) { serverName = 'plex' };
            let catchPlex = (serverName == 'plex' && this._url.indexOf('playQueues?type=video') != -1)
            if (catchPlex && localStorage.getItem(etlpStorageKeys.webPlayerEnable) != 'true') { // Plex
                fetch(this._url, {
                    method: this._method,
                    headers: {
                        'Accept': 'application/json',
                    }
                })
                    .then(response => response.json())
                    .then((res) => {
                        let extraData = {
                            serverName: serverName,
                            gmInfo: GM_info,
                            userAgent: navigator.userAgent,
                        };
                        let data = {
                            playbackData: res,
                            playbackUrl: this._url,
                            mountDiskEnable: localStorage.getItem(etlpStorageKeys.mountDiskEnable),
                            extraData: extraData,
                        };
                        sendDataToLocalServer(data, 'plexToLocalPlayer');
                        removeErrorWindowsMultiTimes();
                    });
                return;
            }
            return originOpen.apply(this, arguments);
        }

        XMLHttpRequest.prototype.send = function (body) {

            let catchJellyfin = (this._method === 'POST' && this._url.endsWith('PlaybackInfo'))
            if (catchJellyfin && localStorage.getItem(etlpStorageKeys.webPlayerEnable) != 'true') { // Jellyfin 10.10
                let pbUrl = this._url;
                body = JSON.parse(body);
                let _body = {};
                ['MediaSourceId', 'StartTimeTicks', 'UserId', 'SubtitleStreamIndex', 'AudioStreamIndex',].forEach(key => {
                    if (body[key] != undefined) {
                        _body[key] = body[key];
                    }
                });
                let query = new URLSearchParams(_body).toString();
                pbUrl = `${pbUrl}?${query}`
                let options = {
                    headers: this._headers,
                };
                dealWithPlaybackInfo(pbUrl, pbUrl, options);
                return;
            }
            originSend.apply(this, arguments);
        }
    }

    initXMLHttpRequest();

    setModeSwitchMenu(etlpStorageKeys.webPlayerEnable, 'Script on this server is ', '', 'Available', 'Disabled', 'Available');
    setModeSwitchMenu(etlpStorageKeys.mountDiskEnable, 'Read disk mode is ');

    function showGuiMenu() {
        sendDataToLocalServer({ 'showTaskManager': true }, 'embyToLocalPlayer');
    }
    if ('etlpTaskManager' in localStorage) {
        setCallbackMenu('View cache tasks', showGuiMenu);
    }

    overwriteConfByStore();

    if (config.resumeHideSomeSeries || localStorage.getItem(etlpStorageKeys.resumeHide) === 'true') {
        setCallbackMenu('Continue Watching: Hide this TV series', hideCurrentSeries);
        setCallbackMenu('Continue Watching: Reset hide settings', resetHiddenSeries);
    }

    // let debounceTimer; # Some CSS selectors are broad, so checking after playback is safer.
    // const observer = new MutationObserver(() => {
    //     clearTimeout(debounceTimer);
    //     debounceTimer = setTimeout(removeErrorWindows, 100);
    // });
    // observer.observe(document.body, { childList: true, subtree: true });
})();
