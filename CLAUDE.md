# Spotify userscripts

Userscripts for `open.spotify.com`. One folder per script with its own README; `tools/` and `tests/` are shared. Code, comments and READMEs are in English. This repository is public: no personal data, keys or real account details.

`test-profile/` holds a Spotify login and must never be committed. `ad-disable/` is local on purpose (see `.gitignore`).

## Adding or changing a script

- `@version` is date-based: `2026.11.09`, then `2026.11.09.1` on the same day. Bump it on every changed version.
- Never change the `@namespace` of a published script: it identifies the script for updates.
- Feedback goes through Greasy Fork, so there is no `@homepageURL` or `@supportURL`.

## Testing

- Tests run against the live page in the separate `test-profile/`, so the user's own Firefox can stay open. Pass `--visible` to `tests/check_*.py` to show the window; music can be audible.
- Injected tests do not prove Tampermonkey behaviour. For a real check, install the Tampermonkey `.xpi` with `driver.install_addon(path, temporary=True)`, serve the script from localhost and ask the user to click Install. WebDriver cannot see that page, and `driver.get` on the script URL blocks unless a short page-load timeout is set.
- A content script without `"world": "MAIN"`, run at `document_start`, is a close stand-in for the userscript sandbox.
- Seeking to the end of a song moves to the next one without using a skip.

## The Spotify page

Use `data-testid` attributes: they do not depend on the interface language, unlike `aria-label`.

| Element | Selector |
|---|---|
| Search field | `input[data-testid="search-input"]` (`aria-expanded` shows the suggestions) |
| Song row | `[data-testid="tracklist-row"]` |
| Big play button | `[data-testid="action-bar-row"] [data-testid="play-button"]` |
| Player bar | `[data-testid="now-playing-bar"]` |
| Current item | `[data-testid="now-playing-widget-v2"]` |
| Play/pause, next | `control-button-playpause`, `control-button-skip-forward` |
| Progress | `playback-progressbar`, `playback-position`, `playback-duration` |
| Mute | `volume-bar-toggle-mute-button` |
| Volume | `[data-testid="volume-bar"] input[type="range"]` (`0` when muted) |

- Title and artist of the current item are in `navigator.mediaSession.metadata`.
- An ad has no album or artist links in the player bar.
- Spotify's internal player object (`playerAPI`) can be found through the React fiber on `#main`.
- The player's media element is a `<video>` that is never added to the page, so it can only be caught in `document.createElement`. Songs play from `blob:` URLs.
- `/` has no function of its own on the page; `Ctrl+/` opens the keyboard shortcuts dialog, which then holds the focus. `Esc` in the search field clears the text but keeps the focus.
- The search suggestions close on a `mousedown` outside of them, not on blur.

## Firefox sandbox and CSP

- Firefox runs userscripts in a sandbox even with `@grant none`. Reach page objects through `element.wrappedJSObject` or `window.wrappedJSObject`.
- Objects created in the sandbox are not readable by the page. Create them in the page (`page.JSON.parse(...)`) or wrap functions with `exportFunction`.
- Never hand the sandbox's `arguments` to a page function: it throws and leaves a blank page. Pass the parameters one by one.
- Spotify's CSP forbids inline scripts but allows `eval`, so code that must run in the page can use `window.wrappedJSObject.eval(...)`.
