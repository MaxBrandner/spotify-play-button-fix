"""Check, without the userscript, that this account can play a song at all."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from browser import start_firefox  # noqa: E402
from spotify_session import (  # noqa: E402
    inject_userscript,
    open_track_search,
    play_row,
    save_failure_screenshot,
    state,
)

QUERY = "Stardust Music Sounds Better With You"
OBSERVE_S = 25


def main():
    driver = start_firefox(headless=False)
    try:
        driver.set_window_size(1400, 900)
        rows = open_track_search(driver, QUERY)
        if not rows:
            print("no result rows, screenshot:", save_failure_screenshot(driver))
            return 1
        print("result rows:", len(rows))
        print("before click:", state(driver))
        play_row(driver, rows[0])

        positions = set()
        problem_seen = False
        last = None
        end = time.time() + OBSERVE_S
        while time.time() < end:
            current = state(driver)
            problem_seen = problem_seen or current["cantPlay"]
            # mediaSession.playbackState can stay "none" while music is playing.
            if current["playerLabel"] == "Pause" and current["position"]:
                positions.add(current["position"])
            summary = {k: current[k] for k in ("title", "playerLabel", "state", "cantPlay")}
            if summary != last:
                print(f"{current['position']}: {summary}")
                last = summary
            time.sleep(0.5)

        advancing = len(positions) >= 10
        print("distinct playing positions:", len(positions))
        print("cannot-play message seen:", problem_seen)
        # Loaded last, so the observation above ran without the userscript.
        print("userscript loaded:", inject_userscript(driver))
        if not advancing or problem_seen:
            print("screenshot:", save_failure_screenshot(driver))
        return 0 if advancing and not problem_seen else 1
    finally:
        driver.quit()


if __name__ == "__main__":
    sys.exit(main())
