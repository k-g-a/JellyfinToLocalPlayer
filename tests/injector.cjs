// Run with NODE_PATH pointing to an installation of jsdom: node tests/injector.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { JSDOM } = require('jsdom');
const source = fs.readFileSync('user_script/embyToLocalPlayer.injector.js', 'utf8');
const tick = () => new Promise(resolve => setTimeout(resolve, 120));
(async () => {
    const dom = new JSDOM('<div class="itemDetailPage"><button class="btnPlay">Play</button><select class="selectAudio"><option value="2" selected>Audio</option></select></div>', {
        url: 'https://jellyfin.test/web/#/details?id=movie', runScripts: 'outside-only',
    });
    const w = dom.window;
    w.HTMLElement.prototype.getClientRects = () => [{}];
    const native = w.document.querySelector('.btnPlay');
    let nativeClicks = 0;
    native.onclick = () => nativeClicks++;
    const posts = [];
    const statuses = [
        { service: 'JellyfinToLocalPlayer', ready: true, title: 'madVR', player: 'hc' },
        { service: 'JellyfinToLocalPlayer', ready: true, player: 'be' },
    ];
    w.fetch = async (url, options) => {
        const index = url.includes(':58001') ? 1 : 0;
        if (options.method === 'POST') {
            posts.push({ url, data: JSON.parse(options.body) });
            return { ok: true };
        }
        if (!statuses[index]) throw Error('offline');
        return { ok: true, json: async () => statuses[index] };
    };
    const fetch = w.fetch, xhr = w.XMLHttpRequest;
    w.ApiClient = {
        getCurrentUserId: () => 'user', deviceId: () => 'device', accessToken: () => 'token',
        serverAddress: () => 'https://jellyfin.test',
        getItem: async () => ({ Id: 'movie', Type: 'Movie', Name: 'Test' }),
        getPlaybackInfo: async () => ({ MediaSources: [{ Id: 'movie' }], PlaySessionId: 'session' }),
    };
    const script = source.replace('const SETTINGS = {};', 'const SETTINGS = { probeIntervalAvailableMs: 30, probeIntervalUnavailableMs: 30 };');
    w.eval(script);
    await tick();
    const buttons = () => [...w.document.querySelectorAll('.etlp-player-button')];
    assert.deepEqual(buttons().map(b => b.textContent), ['Play in madVR', 'Play in be']);
    assert.equal(native.nextElementSibling, buttons()[0]);
    for (const button of buttons()) { button.click(); await tick(); }
    assert.deepEqual(posts.map(p => new URL(p.url).port), ['58000', '58001']);
    assert(posts.every(p => !('playerProfile' in p.data)));
    assert(posts.every(p => p.data.playbackUrl.includes('AudioStreamIndex=2')));
    statuses[0] = null;
    await tick();
    assert.deepEqual(buttons().map(b => b.textContent), ['Play in be']);
    statuses[1] = { service: 'unrelated', ready: true };
    await tick();
    assert.equal(buttons().length, 0);
    statuses[0] = { service: 'JellyfinToLocalPlayer', ready: true, title: '<b>mpv</b>' };
    await tick();
    assert.equal(buttons()[0].textContent, 'Play in <b>mpv</b>');
    assert.equal(buttons()[0].querySelector('b'), null);
    w.eval(script);
    await tick();
    assert.equal(buttons().length, 1);
    native.click();
    assert.equal(nativeClicks, 1);
    assert.equal(w.fetch, fetch);
    assert.equal(w.XMLHttpRequest, xhr);
    w.location.hash = '#/home';
    await tick();
    assert.equal(buttons().length, 0);
    dom.window.close();
    console.log('Injector: discovery, independent failure/recovery, labels, routing, tracks, navigation and globals passed');
})().catch(error => { console.error(error); process.exit(1); });
