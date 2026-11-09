// ==UserScript==
// @name         Spotify Web: Press / to search
// @namespace    spotify-slash-search
// @version      2026.11.09.1
// @description  Press / anywhere in the Spotify web player to jump to the search field, Esc to leave it again.
// @author       MaxBrandner
// @license      MIT
// @match        https://open.spotify.com/*
// @icon         https://open.spotifycdn.com/cdn/images/favicon32.b64ecc03.png
// @run-at       document-idle
// @grant        none
// ==/UserScript==

(function () {
  'use strict';

  const SEARCH_INPUT = 'input[data-testid="search-input"]';
  const NON_TEXT_INPUTS = new Set([
    'button', 'checkbox', 'color', 'file', 'image', 'radio', 'range', 'reset', 'submit',
  ]);

  function acceptsText(element) {
    if (!(element instanceof Element)) return false;
    if (element.isContentEditable) return true;
    if (element.tagName === 'TEXTAREA') return true;
    return element.tagName === 'INPUT' && !NON_TEXT_INPUTS.has(element.type);
  }

  // Capture phase on window, so the page cannot swallow the key first.
  // Shift stays allowed: on many layouts (e.g. German) / is Shift+7.
  window.addEventListener('keydown', (event) => {
    if (event.isComposing) return;
    const input = document.querySelector(SEARCH_INPUT);
    if (!input) return;

    // Spotify's own Esc only clears the text and keeps the focus in the field.
    if (event.key === 'Escape') {
      if (event.target !== input) return;
      event.preventDefault();
      event.stopPropagation();
      input.blur();
      // The suggestion dropdown only closes on a press outside of it.
      document.body.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
      return;
    }

    if (event.key !== '/' || event.ctrlKey || event.metaKey || event.altKey) return;
    if (acceptsText(event.target)) return;

    // Also stops Firefox's quick find, which opens on /.
    event.preventDefault();
    event.stopPropagation();
    input.focus();
    input.select();
  }, true);
})();
