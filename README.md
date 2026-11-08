# Spotify Web: Detach play buttons from the old session

> [!CAUTION]
> **Do not switch this repository to public as it is.** The author and committer fields of its commits contain a private e-mail address. Remove it from the history or publish a fresh copy first.

A userscript for the Spotify web player. If you start something with a play button and Autoplay later takes over, that button stays bound to the old playback: it shows ⏸ and pauses an unrelated song when clicked. With this script, it starts its own music again instead.

## Behaviour

The script looks at every play button outside the player bar and checks whether the current song still belongs to what the button stands for:

| Button | Still belongs when … |
|---|---|
| Song | this exact song is playing |
| Album, single | the song is from this album |
| Artist | the song is by this artist |
| Playlist | the playlist is playing and the song does not come from Autoplay |
| Liked Songs | the song does not come from Autoplay |

**If it still belongs**, nothing changes: the button is a normal play/pause button.

**If it no longer belongs:**

- **Icon:** the button shows ▶ instead of ⏸. The normal icon returns as soon as playback comes from there again.
- **Click while something else is playing:** the button's music starts from its first song, without changing the page.
- **Click while playback is paused:** Spotify gets the click first. If it only resumes the old song, the script corrects this within a few seconds and starts the right music.

These stay unchanged:

- the play/pause button in the player bar
- all buttons during an ad
- podcasts and audiobooks

Detection also works with the keyboard and does not depend on the language of the Spotify interface.

## Limitations

- **Tested** with Firefox, Tampermonkey, a Free account and the English interface. Other browsers, Premium accounts and real interfaces in other languages are untested; language independence was only checked with simulated labels.
- **Depends on Spotify:** the script uses internal details of the page, namely `data-testid` attributes, the shapes of the play and pause icons, and Spotify's internal player object. A Spotify update can break this at any time. The buttons then usually behave as they would without the script.
- **Playlists and Liked Songs** can only be judged through Spotify's internal player object. If it cannot be reached, these buttons stay unchanged.
- **Songs with the same name** by the same artist count as the same song, for example two versions of a title. The other version's button then stays unchanged.
- **Restarted songs** play on their own, not as part of the list they were clicked in. Autoplay takes over afterwards.
- **Fallback:** if Spotify's internal player object cannot be reached or starts nothing, the script briefly opens the item's page instead and then goes back.
- **Free accounts:** an ad can play before the restarted song, and Spotify's limits on skips and on choosing specific songs can prevent a restart.
- **Error messages:** if something could not be started, a message with the prefix `[spotify-restart-fix]` appears in the browser console.
