"""Helpers to drive the Spotify web player in the test browser."""
import time
from pathlib import Path
from urllib.parse import quote

from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By

ROOT = Path(__file__).resolve().parent.parent
USERSCRIPT = ROOT / "spotify-play-button-fix.user.js"
FAILURE_SCREENSHOT = ROOT / ".cache" / "last_failure.png"

ROW = '[data-testid="tracklist-row"]'
PLAYER = '[data-testid="control-button-playpause"]'
PROGRESS = '[data-testid="playback-progressbar"]'
BIG_PLAY = '[data-testid="action-bar-row"] [data-testid="play-button"]'

STATE_JS = """
const md = navigator.mediaSession && navigator.mediaSession.metadata;
const player = document.querySelector('[data-testid="control-button-playpause"]');
const widget = document.querySelector('[data-testid="now-playing-widget-v2"]');
const album = widget && widget.querySelector('a[href*="/album/"]');
const position = document.querySelector('[data-testid="playback-position"]');
return {
  title: md ? md.title : null,
  artist: md ? md.artist : null,
  state: navigator.mediaSession ? navigator.mediaSession.playbackState : null,
  playerLabel: player ? player.getAttribute('aria-label') : null,
  album: album ? album.getAttribute('href') : null,
  position: position ? position.textContent : null,
  cantPlay: /can.t play this/i.test(document.body.innerText),
  path: location.pathname,
};
"""

# Loaded once per page. The prefix filter keeps only the userscript's own logs.
INJECT_JS = """
if (window.__srfLoaded) return false;
window.__srfLoaded = true;
window.__srfLogs = [];
const original = console.log;
console.log = function (...args) {
  if (args[0] === '[spotify-restart-fix]') window.__srfLogs.push(args.slice(1).join(' '));
  return original.apply(this, args);
};
(0, eval)(arguments[0]);
return true;
"""


def state(driver):
    return driver.execute_script(STATE_JS)


def inject_userscript(driver, expose=False):
    """Run the userscript in the page; a full page load removes it again.

    With expose=True its internals are available as window.__srf.
    """
    source = USERSCRIPT.read_text(encoding="utf-8")
    if expose:
        head, tail = source.rsplit("})();", 1)
        source = head + "window.__srf = { itemOf, isIn, nowPlaying };\n})();" + tail
    return driver.execute_script(INJECT_JS, source)


def userscript_logs(driver):
    return driver.execute_script("return window.__srfLogs || []")


def wait_for(condition, timeout, interval=0.25):
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = condition()
        if value:
            return value
        time.sleep(interval)
    return None


def open_track_search(driver, query):
    """Open the song results for a query and return the result rows."""
    driver.get(f"https://open.spotify.com/search/{quote(query)}/tracks")
    return wait_for(lambda: driver.find_elements(By.CSS_SELECTOR, ROW), 30)


def real_click(driver, element):
    """Hover and click with trusted input events, like a user would."""
    ActionChains(driver).move_to_element(element).pause(0.3).click().perform()


def play_row(driver, row):
    """Click the play button of a tracklist row."""
    ActionChains(driver).move_to_element(row).pause(0.4).perform()
    button = row.find_element(By.CSS_SELECTOR, 'button[aria-label^="Play"]')
    real_click(driver, button)


def player_button(driver):
    return driver.find_element(By.CSS_SELECTOR, PLAYER)


def player_is_playing(driver):
    return state(driver)["playerLabel"] == "Pause"


def wait_for_music(driver, timeout=90):
    """Wait until a real song is loaded; ads have no album link."""
    return wait_for(lambda: state(driver)["album"], timeout, 0.5)


def ensure_playing(driver):
    wait_for_music(driver)
    if not player_is_playing(driver):
        real_click(driver, player_button(driver))
        wait_for(lambda: player_is_playing(driver), 5)


def seek_to_end(driver):
    """Jump to the end of the song, which costs no skip, and wait for the next."""
    ensure_playing(driver)
    before = state(driver)["title"]
    bar = driver.find_element(By.CSS_SELECTOR, PROGRESS)
    offset = int(0.485 * bar.size["width"])
    ActionChains(driver).move_to_element_with_offset(bar, offset, 0).pause(0.2).click().perform()
    wait_for(lambda: state(driver)["title"] != before, 25)
    time.sleep(1.5)
    wait_for_music(driver)
    time.sleep(1.5)


def save_failure_screenshot(driver):
    FAILURE_SCREENSHOT.parent.mkdir(exist_ok=True)
    driver.save_screenshot(str(FAILURE_SCREENSHOT))
    return FAILURE_SCREENSHOT
