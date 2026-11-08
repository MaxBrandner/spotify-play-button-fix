"""Check the userscript's core behaviour against the real Spotify page.

Opens a visible test browser and plays music. Autoplay is reached by seeking to
the end of a song, which does not use up the skips of a free account.

The playlist scenario needs a short playlist of your own, kept out of the repo:
SPOTIFY_TEST_PLAYLIST=<playlist id>
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from browser import start_firefox  # noqa: E402
from selenium.webdriver import ActionChains  # noqa: E402
from selenium.webdriver.common.by import By  # noqa: E402
from spotify_session import (  # noqa: E402
    BIG_PLAY,
    ROW,
    ensure_playing,
    inject_userscript,
    open_track_search,
    play_row,
    player_button,
    player_is_playing,
    real_click,
    seek_to_end,
    state,
    userscript_logs,
    wait_for,
    wait_for_music,
)

TITLE = "Music Sounds Better With You"
QUERY = "Stardust Music Sounds Better With You"
TRACK = "/track/303ccTay2FiDTZ9fZ2AdBt"
ALBUM = "/album/7Kusf5plZjl76X5ARWJbNO"
ARTIST = "/artist/2w7IutHv5g4e8LumrwtjWR"
BASE = "https://open.spotify.com"

MAX_LEAVE_TRIES = 8
PAUSED_RESTART_LIMIT_S = 2.5

results = []


def check(name, passed, detail=""):
    results.append(passed)
    print(f"{'PASS' if passed else 'FAIL'}  {name}  {detail}")


def open_page(driver, path, css):
    driver.get(BASE + path)
    wait_for(lambda: driver.find_elements(By.CSS_SELECTOR, css), 25)
    time.sleep(2.5)
    inject_userscript(driver, expose=True)


def is_bound(driver, button):
    return driver.execute_script("return arguments[0].dataset.srfBound === '1'", button)


def label(button):
    return button.get_attribute("aria-label") or ""


def own_song_page_pauses_normally(driver):
    open_page(driver, TRACK, BIG_PLAY)
    wait_for_music(driver)
    big = lambda: driver.find_element(By.CSS_SELECTOR, BIG_PLAY)  # noqa: E731
    if state(driver)["title"] != TITLE or not player_is_playing(driver):
        real_click(driver, big())
        # The first start after opening the browser can take a while.
        wait_for(lambda: state(driver)["title"] == TITLE and player_is_playing(driver), 20)
    if not player_is_playing(driver):
        check("own song page: its song starts", False, state(driver)["title"] or "")
        return
    real_click(driver, big())
    paused = wait_for(lambda: not player_is_playing(driver), 3)
    check("own song page: big button pauses its song", bool(paused), str(userscript_logs(driver)))
    real_click(driver, big())
    wait_for(lambda: player_is_playing(driver), 3)


def row_button(driver):
    row = driver.find_elements(By.CSS_SELECTOR, ROW)[0]
    ActionChains(driver).move_to_element(row).pause(0.4).perform()
    return driver.execute_script(
        "return [...arguments[0].querySelectorAll('button[aria-label]')]"
        ".find(b => /^(play|pause)\\b/i.test(b.getAttribute('aria-label')))",
        row,
    )


def reach_bound_row(driver):
    open_track_search(driver, QUERY)
    time.sleep(2.5)
    inject_userscript(driver, expose=True)
    wait_for_music(driver)
    if state(driver)["title"] != TITLE:
        play_row(driver, driver.find_elements(By.CSS_SELECTOR, ROW)[0])
        wait_for(lambda: state(driver)["title"] == TITLE, 6)
    ensure_playing(driver)
    seek_to_end(driver)
    return row_button(driver)


def bound_row_restarts_its_song(driver):
    button = reach_bound_row(driver)
    check("bound row shows the play icon", is_bound(driver, button), label(button))
    search_path = state(driver)["path"]
    real_click(driver, row_button(driver))
    started = wait_for(lambda: state(driver)["title"] == TITLE, 5)
    wait_for(lambda: state(driver)["path"] == search_path, 3)
    check("bound row restarts its song", bool(started), state(driver)["position"] or "")
    check("page returns after restart", state(driver)["path"] == search_path)


def paused_bound_row_restarts_quickly(driver):
    reach_bound_row(driver)
    real_click(driver, player_button(driver))
    wait_for(lambda: not player_is_playing(driver), 3)
    time.sleep(1)
    button = row_button(driver)  # hovering must not count towards the time
    start = time.time()
    real_click(driver, button)
    started = wait_for(lambda: state(driver)["title"] == TITLE, 6)
    elapsed = time.time() - start
    check(
        "paused bound row restarts quickly",
        bool(started) and elapsed < PAUSED_RESTART_LIMIT_S,
        f"{elapsed:.1f}s",
    )


def album_card(driver):
    card = driver.execute_script(
        "return [...document.querySelectorAll('[data-encore-id=\"card\"]')]"
        ".find(c => c.querySelector(`a[href=\"${arguments[0]}\"]`))",
        ALBUM,
    )
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'})", card)
    time.sleep(0.5)
    ActionChains(driver).move_to_element(card).pause(0.4).perform()
    return card.find_element(By.CSS_SELECTOR, '[data-testid="play-button"]')


def leave_album(driver):
    for _ in range(MAX_LEAVE_TRIES):
        if state(driver)["album"] not in (ALBUM, None):
            return True
        seek_to_end(driver)
    return False


def bound_album_card_restarts(driver):
    open_page(driver, ARTIST, ROW)
    ensure_playing(driver)
    if not leave_album(driver):
        check("album card: could leave the album", False)
        return
    real_click(driver, album_card(driver))
    wait_for(lambda: state(driver)["album"] == ALBUM, 6)
    leave_album(driver)
    button = album_card(driver)
    if not label(button).startswith("Pause"):
        print("SKIP  album card: Spotify did not bind this button in this run")
        return
    check("bound album card shows the play icon", is_bound(driver, button), label(button))
    real_click(driver, button)
    started = wait_for(lambda: state(driver)["album"] == ALBUM, 6)
    check("bound album card restarts its album", bool(started), state(driver)["title"] or "")
    check("no restart failure logged", not userscript_logs(driver), str(userscript_logs(driver)))


def bound_playlist_button_restarts(driver):
    playlist_id = os.environ.get("SPOTIFY_TEST_PLAYLIST")
    if not playlist_id:
        print("SKIP  playlist: SPOTIFY_TEST_PLAYLIST is not set")
        return
    open_page(driver, f"/playlist/{playlist_id}", BIG_PLAY)
    wait_for_music(driver)
    big = lambda: driver.find_element(By.CSS_SELECTOR, BIG_PLAY)  # noqa: E731
    still_in = lambda: driver.execute_script(  # noqa: E731
        "return window.__srf.isIn({type: 'playlist', id: arguments[0]})", playlist_id
    )
    first_title = driver.execute_script(
        f"return document.querySelector('{ROW} a[href*=\"/track/\"]').textContent"
    )
    if not still_in() or not player_is_playing(driver):
        real_click(driver, big())
        wait_for(lambda: still_in() and player_is_playing(driver), 6)
    for _ in range(MAX_LEAVE_TRIES):
        if not still_in():
            break
        seek_to_end(driver)
    check("playlist: left through Autoplay", not still_in(), state(driver)["title"] or "")
    check("bound playlist button shows the play icon", is_bound(driver, big()), label(big()))
    real_click(driver, big())
    started = wait_for(lambda: state(driver)["title"] == first_title, 6)
    check("bound playlist button restarts at song 1", bool(started), state(driver)["title"] or "")


def bound_liked_songs_button_restarts(driver):
    open_page(driver, "/collection/tracks", BIG_PLAY)
    wait_for_music(driver)
    rows = driver.find_elements(By.CSS_SELECTOR, ROW)
    if not rows:
        print("SKIP  Liked Songs: this account has none")
        return
    big = lambda: driver.find_element(By.CSS_SELECTOR, BIG_PLAY)  # noqa: E731
    still_in = lambda: driver.execute_script(  # noqa: E731
        "return window.__srf.isIn({type: 'collection', id: 'tracks'})"
    )
    first_title = driver.execute_script(
        f"return document.querySelector('{ROW} a[href*=\"/track/\"]').textContent"
    )
    # Starting at the last song reaches Autoplay after one seek.
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'})", rows[-1])
    time.sleep(0.6)
    play_row(driver, rows[-1])
    wait_for(lambda: still_in() and player_is_playing(driver), 6)
    for _ in range(MAX_LEAVE_TRIES):
        if not still_in():
            break
        seek_to_end(driver)
    check("Liked Songs: left through Autoplay", not still_in(), state(driver)["title"] or "")
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'})", big())
    time.sleep(0.6)
    check("bound Liked Songs button shows the play icon", is_bound(driver, big()), label(big()))
    real_click(driver, big())
    started = wait_for(lambda: state(driver)["title"] == first_title, 6)
    check("bound Liked Songs button restarts at song 1", bool(started), state(driver)["title"] or "")


def main():
    driver = start_firefox(headless=False)
    try:
        driver.set_window_size(1400, 900)
        for scenario in (
            own_song_page_pauses_normally,
            bound_row_restarts_its_song,
            paused_bound_row_restarts_quickly,
            bound_album_card_restarts,
            bound_playlist_button_restarts,
            bound_liked_songs_button_restarts,
        ):
            scenario(driver)
    finally:
        driver.quit()
    print(f"{sum(results)}/{len(results)} checks passed")
    return 0 if results and all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
