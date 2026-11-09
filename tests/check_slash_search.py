"""Check on the live page that / moves the focus to the search field."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from selenium.webdriver import ActionChains, Keys  # noqa: E402
from selenium.webdriver.common.by import By  # noqa: E402

from browser import ROOT, start_firefox  # noqa: E402

SCRIPT = ROOT / "slash-search" / "spotify-slash-search.user.js"
SEARCH = 'input[data-testid="search-input"]'
PAGE_TIMEOUT_S = 40
SETTLE_S = 0.4

ACTIVE_IS_SEARCH = f"return document.activeElement === document.querySelector('{SEARCH}')"
BLUR = "document.activeElement.blur()"
DROPDOWN_OPEN = f"return document.querySelector('{SEARCH}').getAttribute('aria-expanded')"
SHIFT_SLASH = """
const event = new KeyboardEvent('keydown', {
  key: '/', shiftKey: true, bubbles: true, cancelable: true,
});
document.body.dispatchEvent(event);
return event.defaultPrevented;
"""
ADD_FIELD = """
const field = document.createElement(arguments[0]);
if (arguments[1]) field.type = arguments[1];
if (arguments[2]) field.contentEditable = 'true';
field.id = 'slash-test-field';
field.style.cssText = 'position:fixed;top:0;left:0;z-index:99999;width:200px;height:40px';
document.body.append(field);
field.focus();
"""
FIELD_TEXT = """
const field = document.getElementById('slash-test-field');
return field.value === undefined ? field.textContent : field.value;
"""
REMOVE_FIELD = "document.getElementById('slash-test-field').remove()"
SELECTION = (
    f"const i = document.querySelector('{SEARCH}');"
    "return [i.value, i.selectionStart, i.selectionEnd]"
)

failures = []


def check(name, passed, detail=""):
    print(("ok  " if passed else "FAIL"), name, detail)
    if not passed:
        failures.append(name)


def press(driver, keys):
    ActionChains(driver).send_keys(keys).perform()
    time.sleep(SETTLE_S)


def stays_in_field(driver, name, tag, input_type=None, editable=False):
    driver.execute_script(ADD_FIELD, tag, input_type, editable)
    press(driver, "/")
    check(name, driver.execute_script(FIELD_TEXT) == "/" and not driver.execute_script(ACTIVE_IS_SEARCH))
    driver.execute_script(REMOVE_FIELD)


def main():
    driver = start_firefox(headless="--visible" not in sys.argv)
    try:
        driver.set_window_size(1400, 900)
        driver.get("https://open.spotify.com")
        deadline = time.time() + PAGE_TIMEOUT_S
        while time.time() < deadline and not driver.find_elements(By.CSS_SELECTOR, SEARCH):
            time.sleep(0.25)
        driver.execute_script(SCRIPT.read_text(encoding="utf-8"))

        driver.execute_script(BLUR)
        press(driver, "/")
        check("/ jumps to search", driver.execute_script(ACTIVE_IS_SEARCH))
        check("/ is not typed into search", driver.execute_script(SELECTION)[0] == "")

        press(driver, "abc")
        driver.execute_script(BLUR)
        press(driver, "/")
        selection = driver.execute_script(SELECTION)
        check("existing text is selected", selection == ["abc", 0, 3], str(selection))

        press(driver, "/")
        check("/ can be typed inside search", driver.execute_script(SELECTION)[0] == "/")
        press(driver, Keys.BACKSPACE)

        press(driver, "xyz")
        press(driver, Keys.ESCAPE)
        check("Esc leaves search", not driver.execute_script(ACTIVE_IS_SEARCH))
        check("Esc keeps the text", driver.execute_script(SELECTION)[0] == "xyz")
        expanded = driver.execute_script(DROPDOWN_OPEN)
        check("Esc closes the dropdown", expanded != "true", str(expanded))
        press(driver, "/")
        check("/ jumps back after Esc", driver.execute_script(ACTIVE_IS_SEARCH))
        press(driver, Keys.BACKSPACE)

        stays_in_field(driver, "/ is typed in a text input", "input", "text")
        stays_in_field(driver, "/ is typed in a textarea", "textarea")
        stays_in_field(driver, "/ is typed in contenteditable", "div", None, True)

        driver.execute_script(ADD_FIELD, "input", "range", False)
        press(driver, "/")
        check("/ jumps away from a slider", driver.execute_script(ACTIVE_IS_SEARCH))
        driver.execute_script(REMOVE_FIELD)

        driver.execute_script(BLUR)
        prevented = driver.execute_script(SHIFT_SLASH)
        check("Shift+/ (German layout) jumps", prevented and driver.execute_script(ACTIVE_IS_SEARCH))

        # Last: Ctrl+/ opens Spotify's shortcut dialog, which then holds the focus.
        driver.execute_script(BLUR)
        ActionChains(driver).key_down(Keys.CONTROL).send_keys("/").key_up(Keys.CONTROL).perform()
        time.sleep(SETTLE_S)
        check("Ctrl+/ does not jump", not driver.execute_script(ACTIVE_IS_SEARCH))
    finally:
        driver.quit()
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
