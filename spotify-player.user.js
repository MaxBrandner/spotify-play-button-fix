// ==UserScript==
// @name         Spotify Web: Detach play buttons from the old session
// @namespace    spotify-restart-fix
// @version      2026.11.09.1
// @description  Once playback has moved on (e.g. via Autoplay), play buttons of songs, albums and artists start their own music again instead of pausing or resuming the old session.
// @author       MaxBrandner
// @license      MIT
// @match        https://open.spotify.com/*
// @icon         https://open.spotifycdn.com/cdn/images/favicon32.b64ecc03.png
// @run-at       document-idle
// @grant        none
// ==/UserScript==

(function () {
  'use strict';

  const LOG = (...a) => console.log('[spotify-restart-fix]', ...a);
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  async function waitFor(fn, timeout) {
    const t0 = Date.now();
    while (Date.now() - t0 < timeout) {
      if (fn()) return true;
      await sleep(50);
    }
    return false;
  }

  // ---------- What is currently playing (or paused)? ----------
  // Title/artist come from the Media Session, album and artist IDs from the
  // links in the player bar (it has no link to the track itself).
  function nowPlaying() {
    const md = navigator.mediaSession && navigator.mediaSession.metadata;
    if (!md || !md.title) return null;
    const bar = document.querySelector('[data-testid="now-playing-widget-v2"], [data-testid="now-playing-widget"]');
    return {
      title: md.title.trim(),
      artist: (md.artist || '').trim(),
      albumId: bar ? [...idsIn(bar, 'album')][0] || null : null,
      artistIds: bar ? [...idsIn(bar, 'artist')] : [],
    };
  }
  const currentTitle = () => (nowPlaying() || {}).title || null;

  // Spotify's own player state, reachable through React. It is the only source
  // that tells whether a song comes from a playlist or from Autoplay.
  let playerAPI = null;
  let nextLookup = 0;
  function findPlayerAPI() {
    if (playerAPI || Date.now() < nextLookup) return playerAPI;
    nextLookup = Date.now() + 5000;
    const el = document.querySelector('#main');
    // Firefox hides the page's own properties from sandboxed userscripts.
    const root = el && (el.wrappedJSObject || el);
    const key = root && Object.keys(root).find((k) => k.startsWith('__reactContainer'));
    const stack = key ? [root[key]] : [];
    while (stack.length) {
      const fiber = stack.pop();
      if (!fiber) continue;
      const api = fiber.memoizedProps && fiber.memoizedProps.playerAPI;
      if (api && typeof api.getState === 'function' && typeof api.getQueue === 'function') return (playerAPI = api);
      stack.push(fiber.sibling, fiber.child);
    }
    return null;
  }

  // Is the current song part of what the button stands for?
  // If we can't tell, say yes, so the button keeps its normal behaviour.
  function isIn(item) {
    const np = nowPlaying();
    // Ads have no album or artist links in the player bar.
    if (!np || (!np.albumId && !np.artistIds.length)) return true;
    switch (item.type) {
      case 'track':
        return !item.title || (item.title === np.title &&
          (!item.artist || !np.artist || np.artist.includes(item.artist)));
      case 'album':
        return !np.albumId || np.albumId === item.id;
      case 'artist':
        return !np.artistIds.length || np.artistIds.includes(item.id);
      case 'playlist': {
        const api = findPlayerAPI();
        const state = api && api.getState();
        const current = api && api.getQueue().current;
        if (!state || !state.context || !current) return true;
        // The context stays the playlist during Autoplay; only the queue
        // reliably says where the current song comes from.
        return state.context.uri === `spotify:playlist:${item.id}` && current.provider !== 'autoplay';
      }
      case 'collection': {
        // Liked Songs have no fixed context URI (it can be a generated playlist).
        // A button only shows "Pause" for its own session, so Autoplay is enough.
        const api = findPlayerAPI();
        const current = api && api.getQueue().current;
        return !current || current.provider !== 'autoplay';
      }
    }
    return true;
  }

  // ---------- Which buttons count? ----------
  // Buttons are recognised by their icon, because labels depend on the UI
  // language. Spotify uses a 24 px and a 16 px version of each icon.
  const PLAY_ICONS = ['m7.05 3.606', 'M3 1.713a'];
  const PAUSE_ICONS = ['M5.7 3a', 'M2.7 1a'];

  function iconOf(b) {
    const path = b.querySelector('svg path');
    const d = path ? path.getAttribute('d') || '' : '';
    if (d === PLAY_D) return 'pause'; // our ▶ stands in for Spotify's ⏸
    if (PAUSE_ICONS.some((i) => d.startsWith(i))) return 'pause';
    if (PLAY_ICONS.some((i) => d.startsWith(i))) return 'play';
    return null;
  }
  const showsPause = (b) => iconOf(b) === 'pause';

  // mediaSession.playbackState stays "none", so the player button is the source.
  const playerIsPlaying = () => {
    const b = document.querySelector('[data-testid="control-button-playpause"]');
    return !!b && showsPause(b);
  };

  function isPlayPause(b) {
    if (!b || b.tagName !== 'BUTTON' || b.closest('[data-testid="now-playing-bar"]')) return false;
    return b.dataset.testid === 'play-button' || !!iconOf(b);
  }

  // ---------- What does a button stand for? ----------
  // Returns { type, id, path, title, artist } for songs, albums/singles, artists,
  // playlists and Liked Songs.
  const LIKED = { type: 'collection', id: 'tracks', path: '/collection/tracks', title: 'Liked Songs', artist: '' };
  const ENTITY_SEL = ['track', 'album', 'playlist', 'artist', 'show', 'episode', 'audiobook', 'collection', 'user', 'genre']
    .map((t) => `a[href*="/${t}/"], [id*="spotify:${t}:"]`).join(', ');
  const ROW_SEL = '[data-encore-id="listRow"], [data-testid="tracklist-row"], [role="row"], [role="option"], [role="listitem"], li';

  function idsIn(el, type) {
    const re = new RegExp(`${type}[:/]([A-Za-z0-9]{22})`);
    const ids = new Set();
    for (const x of el.querySelectorAll(`a[href*="/${type}/"], [id*="spotify:${type}:"]`)) {
      const m = (x.tagName === 'A' ? x.getAttribute('href') : x.id).match(re);
      if (m) ids.add(m[1]);
    }
    return ids;
  }

  function describe(el, type, id) {
    const link = el.querySelector(`a[href*="/${type}/${id}"]`);
    const titleEl = el.querySelector(`[id*="spotify:${type}:${id}"], [data-encore-id="listRowTitle"]`);
    const artist = type === 'artist' ? null : el.querySelector('a[href*="/artist/"]');
    return {
      type, id, path: `/${type}/${id}`,
      title: (link ? link.getAttribute('aria-label') || link.textContent
                   : titleEl ? titleEl.textContent : '').trim(),
      artist: artist ? artist.textContent.trim() : '',
    };
  }

  function itemOf(btn) {
    // Big play button on a song, album or artist page, or its copy in the top
    // bar that appears when scrolling: the ID is in the URL
    if (btn.closest('[data-testid="action-bar-row"], [data-testid="topbar-content"]')) {
      if (location.pathname === LIKED.path) return LIKED;
      const m = location.pathname.match(/^\/(track|album|artist|playlist)\/([A-Za-z0-9]{22})/);
      if (!m) return null;
      const title = ((document.querySelector('[data-testid="entityTitle"]') || {}).textContent || '').trim();
      if (m[1] === 'track' && !title) return null;
      return { type: m[1], id: m[2], path: m[0], title, artist: '' };
    }
    // Otherwise walk up to the button's own row/card: the first ancestor that is
    // a list row or links to any Spotify entity, and see what it links to.
    let el = btn;
    for (let i = 0; i < 10; i++) {
      el = el.parentElement;
      if (!el) return null;
      if (!el.matches(ROW_SEL) && !el.querySelector(ENTITY_SEL)) continue;
      const tracks = idsIn(el, 'track');
      if (tracks.size === 1) return describe(el, 'track', [...tracks][0]);
      if (tracks.size) return null;
      if (el.querySelector('a[href="/collection/tracks"], [id*="spotify:collection:tracks"]')) return LIKED;
      const playlists = idsIn(el, 'playlist');
      if (playlists.size === 1) return describe(el, 'playlist', [...playlists][0]);
      if (playlists.size) return null;
      const albums = idsIn(el, 'album');
      if (albums.size === 1) return describe(el, 'album', [...albums][0]);
      if (albums.size) return null;
      const artists = idsIn(el, 'artist');
      if (artists.size === 1) return describe(el, 'artist', [...artists][0]);
      return null;
    }
    return null;
  }

  // ---------- Restart ----------
  // Spotify's own player API starts anything directly, from its first song.
  // Only if that fails we open the item's page: songs may autoplay from their
  // URL, everything else is started by clicking the first song in its list.
  function playViaApi(item) {
    const api = findPlayerAPI();
    if (!api || typeof api.play !== 'function') return false;
    // Arguments must be created in the page, a sandboxed userscript's own
    // objects are not readable there.
    const page = window.wrappedJSObject || window;
    const arg = (value) => page.JSON.parse(JSON.stringify(value));
    try {
      api.play(arg({ uri: `spotify:${item.type}:${item.id}` }), arg({}), arg({ skipTo: { index: 0 } }));
      return true;
    } catch (err) {
      return false;
    }
  }

  function go(url) {
    history.pushState(history.state, '', url);
    window.dispatchEvent(new PopStateEvent('popstate', { state: history.state }));
  }

  const firstRow = () => document.querySelector('[data-testid="tracklist-row"]');
  const firstRowId = () => { const r = firstRow(); return r ? [...idsIn(r, 'track')][0] || null : null; };
  const firstRowBtn = () => {
    const r = firstRow();
    return r && [...r.querySelectorAll('button')].find((b) => iconOf(b) === 'play');
  };

  let busy = false;

  async function restart(item) {
    if (busy) return;
    busy = true;
    const before = currentTitle();
    const started = () => isIn(item) || (currentTitle() && currentTitle() !== before);
    let navigated = false;
    try {
      if (playViaApi(item) && (await waitFor(started, 4000))) return;
      if (item.type === 'track') {
        go(item.path);
        navigated = true;
      } else {
        if (location.pathname !== item.path) {
          const prevRow = firstRow();
          const prev = firstRowId();
          go(item.path);
          navigated = true;
          // The new page's first song can be the same as the old page's.
          await waitFor(() => location.pathname === item.path && firstRowBtn() &&
            (firstRow() !== prevRow || firstRowId() !== prev), 5000);
        }
        const btn = firstRowBtn();
        if (btn) btn.click(); // our own click handler ignores it while busy
      }
      if (!(await waitFor(started, 4000))) LOG(`Could not start "${item.title || item.path}".`);
    } finally {
      if (navigated) history.back();
      busy = false;
    }
  }

  // ---------- Intercept clicks ----------
  // Some places (e.g. the search dropdown) react on mouse down already,
  // so we intercept the whole chain pointerdown … click.
  let swallow = null; // { btn, item, ran }
  let press = null; // { btn, paused, title }, for buttons showing "Play"
  const playback = () => ({ paused: !playerIsPlaying(), title: currentTitle() });

  function onEvent(e) {
    if (swallow && swallow.btn.contains(e.target)) {
      e.preventDefault();
      e.stopImmediatePropagation();
      if (!swallow.ran && (e.type === 'mouseup' || e.type === 'click')) {
        swallow.ran = true;
        restart(swallow.item);
      }
      if (e.type === 'click') swallow = null;
      return;
    }

    if (busy || !['pointerdown', 'mousedown', 'click'].includes(e.type)) return;
    const btn = e.target.closest('button');
    if (!isPlayPause(btn)) return;
    const item = itemOf(btn);
    if (!item || isIn(item)) return; // still playing from here → normal play/pause

    if (showsPause(btn)) {
      // Shows "Pause" although playback has moved on → bound to the old session
      e.preventDefault();
      e.stopImmediatePropagation();
      if (e.type === 'click') { restart(item); return; } // e.g. keyboard activation
      const s = { btn, item, ran: false };
      swallow = s;
      setTimeout(() => { if (swallow === s) swallow = null; }, 1500);
      return;
    }

    // Shows "Play". If something else is playing, the button is not bound and
    // Spotify starts the right music by itself. If the session is paused,
    // Spotify may just resume the old song, so check afterwards (~0.6 s).
    // The state is read on press, because some places start on mouse down.
    if (e.type !== 'click') {
      if (e.type === 'pointerdown' || !press) press = { btn, ...playback() };
      return;
    }
    const { paused, title: before } = press && press.btn === btn ? press : playback();
    press = null;
    if (!paused || !before) return;
    const t0 = Date.now();
    const resumed = () => playerIsPlaying() && Date.now() - t0 > 600;
    waitFor(() => currentTitle() !== before || resumed(), 2000).then(() => {
      if (currentTitle() === before && !busy && !isIn(item)) restart(item);
    });
  }

  for (const t of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {
    window.addEventListener(t, onEvent, true);
  }

  // ---------- Visuals: bound buttons show ▶ instead of ⏸ ----------
  // The trailing space tells our icon apart from Spotify's own play icon.
  const PLAY_D = 'm7.05 3.606 13.49 7.788a.7.7 0 0 1 0 1.212L7.05 20.394A.7.7 0 0 1 6 19.788V4.212a.7.7 0 0 1 1.05-.606 ';

  function setPlayIcon(btn) {
    const svg = btn.querySelector('svg');
    const paths = svg ? svg.querySelectorAll('path') : [];
    if (!paths.length) return;
    svg.dataset.srfVb = svg.getAttribute('viewBox') || '';
    svg.setAttribute('viewBox', '0 0 24 24');
    paths[0].dataset.srfD = paths[0].getAttribute('d') || '';
    paths[0].setAttribute('d', PLAY_D);
    for (const p of [...paths].slice(1)) { p.style.display = 'none'; p.dataset.srfHidden = '1'; }
    btn.dataset.srfBound = '1';
  }

  function restoreIcon(btn) {
    const svg = btn.querySelector('svg');
    if (svg) {
      const p0 = svg.querySelector('path');
      if (p0 && p0.getAttribute('d') === PLAY_D && p0.dataset.srfD) p0.setAttribute('d', p0.dataset.srfD);
      if (svg.getAttribute('viewBox') === '0 0 24 24' && svg.dataset.srfVb) svg.setAttribute('viewBox', svg.dataset.srfVb);
      for (const p of svg.querySelectorAll('[data-srf-hidden]')) { p.style.display = ''; delete p.dataset.srfHidden; }
    }
    delete btn.dataset.srfBound;
  }

  function paint() {
    for (const btn of document.querySelectorAll('button[aria-label]')) {
      if (!isPlayPause(btn)) continue;
      const marked = btn.dataset.srfBound === '1';
      const pause = showsPause(btn);
      if (!marked && !pause) continue;
      const item = pause ? itemOf(btn) : null;
      const bound = !!item && !isIn(item);
      if (bound && !marked) setPlayIcon(btn);
      else if (!bound && marked) restoreIcon(btn);
    }
  }

  let paintTimer = null;
  new MutationObserver(() => {
    if (paintTimer) return;
    paintTimer = setTimeout(() => { paintTimer = null; paint(); }, 200);
  }).observe(document.body, {
    subtree: true, childList: true, characterData: true,
    attributes: true, attributeFilter: ['aria-label'],
  });
  paint();
})();
