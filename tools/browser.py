"""Start the isolated test Firefox under WebDriver control."""
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "test-profile"

# Keep the downloaded geckodriver inside the project.
os.environ.setdefault("SE_CACHE_PATH", str(ROOT / ".cache" / "selenium"))

from selenium import webdriver  # noqa: E402
from selenium.webdriver.firefox.options import Options  # noqa: E402


def prepare_profile():
    PROFILE.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "tools" / "user.js", PROFILE / "user.js")


def start_firefox(headless=False):
    prepare_profile()
    options = Options()
    # Passed as arguments so Selenium uses this profile instead of a temp copy.
    options.add_argument("-profile")
    options.add_argument(str(PROFILE))
    if headless:
        options.add_argument("-headless")
    return webdriver.Firefox(options=options)
