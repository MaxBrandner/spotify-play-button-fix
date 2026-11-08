"""Check that the test profile starts, reaches Spotify and has Widevine."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from browser import PROFILE, start_firefox  # noqa: E402

WIDEVINE_TIMEOUT_S = 120

PROBE = """
const done = arguments[arguments.length - 1];
navigator.requestMediaKeySystemAccess('com.widevine.alpha', [{
  initDataTypes: ['cenc'],
  audioCapabilities: [{contentType: 'audio/mp4; codecs="mp4a.40.2"'}],
}]).then(() => done('ok'), e => done(String(e)));
"""


def main():
    driver = start_firefox(headless="--visible" not in sys.argv)
    try:
        driver.set_script_timeout(30)
        driver.get("https://open.spotify.com")
        print("title:", driver.title)
        print("user agent:", driver.execute_script("return navigator.userAgent"))
        deadline = time.time() + WIDEVINE_TIMEOUT_S
        result = "not run"
        while time.time() < deadline:
            installed = any((PROFILE / "gmp-widevinecdm").glob("*/*widevine*"))
            result = driver.execute_async_script(PROBE)
            if installed and result == "ok":
                break
            time.sleep(5)
        print("widevine installed:", installed)
        print("widevine probe:", result)
        logged_in = driver.execute_script(
            "return !!document.querySelector('[data-testid=\"user-widget-link\"]')"
        )
        print("logged in:", logged_in)
        return 0 if installed and result == "ok" else 1
    finally:
        driver.quit()


if __name__ == "__main__":
    sys.exit(main())
