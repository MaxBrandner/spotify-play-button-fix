# Spotify Web: Press / to search

A userscript for the Spotify web player. Press `/` anywhere to jump to the search field and start typing, without reaching for the mouse. Press `Esc` to leave the field again.

<!-- Add the Greasy Fork install link here after publishing. -->

## Behaviour

| Key | Where | What happens |
|---|---|---|
| `/` | anywhere outside a text field | the cursor moves to the search field |
| `/` | inside a text field, including the search field | a normal `/` is typed |
| `Esc` | in the search field | the cursor leaves the field and the suggestions close |

- **Existing search text** is selected when you jump to the field, so you can type over it right away.
- **After `Esc`** your search text stays in the field. Spotify's own `Esc` would clear it and keep the cursor there.
- **Sliders and buttons:** `/` also works while the volume or progress slider has focus.
- **Key combinations:** `Ctrl`, `Alt` or `Cmd` with `/` are left alone, so `Ctrl+/` still opens Spotify's list of keyboard shortcuts.
- **Keyboard layouts:** the script reacts to the `/` character, so it also works on layouts where `/` needs `Shift`.
- **Firefox:** the script replaces Firefox's quick find, which normally opens on `/`, on the Spotify page.

## Limitations

- **Tested** with Firefox, Tampermonkey, a Free account and the English interface. Other browsers and Premium accounts are untested. `/` on layouts that need `Shift` was only checked with a simulated key press.
- **Depends on Spotify:** the script finds the search field through its `data-testid` attribute. A Spotify update can break this at any time. The `/` key then does nothing on the page.
- **Shortcut dialog:** while Spotify's keyboard shortcuts dialog is open, `/` may not reach the search field.
