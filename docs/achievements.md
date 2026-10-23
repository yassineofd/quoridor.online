# Achievements, score and rank

Every finished game earns points; achievements earn more; the score decides the player's rank. It is there to give people a
reason to come back: a next goal is always on screen, a streak of days rewards coming back tomorrow, and the top ranks are far enough away to
stay interesting.

There are no accounts, so all of it lives in the player's browser (`localStorage`, one entry named `quoridor.progress`). Nothing is sent
to the server, it is not shared between devices, and clearing the site data starts it over. The Privacy Policy says so
(`PROGRESS_STORAGE` in `pages.py`).

## What the player sees

| Where | What |
|---|---|
| End of a game (all modes) | A reward block in the result panel: points earned, new rank, the achievements just unlocked, the way to the next rank, the day streak |
| Under every play form (`/play/*`, `/variants/*`) | A short summary: rank, score, the next goal with a progress bar, a nudge to keep a day streak |
| `/achievements` | Rank and progress to the next, statistics, every achievement in six groups (locked ones show their progress), reset button |
| `/play` | A card that points to the page |
| Footer | "Achievements" link on every page |

## What counts

* A game counts when it has **at least 6 moves** (`MIN_MOVES`). A game abandoned at once earns nothing.
* A game counts when this page **saw it being played**. Opening a finished online room again does not count it a second time
  (`seenLive` in `game.js`); a rematch in the same room is a new game.
* **Wins** are against the robot or an online player. A game on one device has no "you", so it only counts as played (and towards
  Pass the device and the variants), never as a win. That keeps the win counts from being farmed by playing both sides.
* The skill achievements (Straight to the goal, Pure runner, Fortress, Comeback) need a win **by reaching the goal**, not by the other side
  resigning, leaving or running out of time.
* Points for a game: 5 for finishing, +10 for a win, + a bonus for the opponent (Medium 5, Hard 15, Expert 30, an online player 20).
* Ranks (`RANKS` in `achievements.js`): 0, 75, 200, 400, 700, 1100, 1700 points. The score is the game points plus the points of the unlocked
  achievements, added up when it is read, so changing an achievement's points changes everyone's score at once.
* A day streak counts local calendar days (a day with at least one counted game). It is still alive the day after the last game and gone
  after that; the best streak is kept.

## Files

| File | Role |
|---|---|
| `static/assets/js/achievements.js` | The catalogue, ranks, storage and `recordGame()`. No DOM. Replays the moves with the engine to find jumps, detours and comebacks |
| `static/assets/js/achievements-ui.js` | Draws the reward block, the summary under the forms and the Achievements page (all from messages, so it follows the language) |
| `static/assets/js/game.js` | Calls `recordGame()` once when a game ends and puts the reward block in the result panel |
| `pages.py` (`achievements()`, `PROGRESS_SCRIPTS`, `stage()`) | The page, the scripts each page loads, the summary container under every play form |
| `translations/js-en.json` (`ach.*`) | Every text: `ach.<id>.name`, `ach.<id>.desc`, `ach.rank.<n>`, `ach.cat.<group>` and the interface |
| `tests/achievements.html`, `tests/test_achievements.py` | The logic, played with the real engine against a stand-in for `localStorage` |

## Adding an achievement

1. Add it to `CATALOG` in `achievements.js`: `counter(id, icon, points, group, target, valueFunction)` for something that counts up (it gets a progress bar and can
   be the suggested next goal), or `event(id, icon, points, group, test)` for something one game does. `icon` is a name from `_ICONS` in `lib.py`.
2. Add `ach.<id>.name` and `ach.<id>.desc` to `translations/js-en.json`.
3. Translate them: `python i18n.py missing es` (and the other languages), then `python i18n.py check`.
4. Add a case to `tests/achievements.html` if it is an event, and run `python -m unittest tests.test_achievements`.

Existing players get a new counter achievement the next time they finish a game, if they already meet it. An event can only be earned in a new game.
The saved record is checked on every read (`sanitize()`), so an old, damaged or hand-edited entry cannot break the page.

## Changing the stored data

`quoridor.progress` has a `v` field (1). Add fields freely: `sanitize()` fills in what is missing. If a field ever changes meaning, bump `v` and
convert in `sanitize()`.
