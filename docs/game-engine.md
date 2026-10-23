# Game engine and playing modes

How the four ways to play are built. The site spec is in `architecture-spec.md`; this is the engine side.

| Mode | Page | Where the game runs | Needs the Python server? |
|---|---|---|---|
| Play with a friend (same device) | `/play/local/` | Browser | No |
| Play against the robot | `/play/computer/` | Browser (computer opponent in a Web Worker) | No |
| Private room | `/play/create-room/`, `/play/join-room/`, `/room/<id>/` | Server is authoritative | Yes |
| Online matchmaking | `/play/online/` (then `/room/<id>/`) | Server is authoritative | Yes |

Local and computer play are plain static files, so they work on any static host. Online play needs
`serve.py` (or anything that mounts `server/api.py`) behind the same origin as the site.

## Rules implemented

Exactly the rules on `/quoridor-rules/`: 9x9 board, 10 walls each, one pawn move or one wall per turn,
straight jumps and diagonal side-steps when the jump is blocked, walls are 2 wide and may not overlap, cross
at the middle or leave either pawn without a route (pawns are ignored by that check). First pawn on the
opposite edge wins. Player 0 (cyan filled pawn, starts at the bottom, `e1`) always moves first in same-device and
computer games. In online games the server picks who is seat 0 (random); a rematch swaps seats.

## Variants

A variant is a row in `VARIANTS` at the top of `engine.js`: board size (`rows`, `cols`), the two start squares, the two goal rows
and the walls each player gets. `new Quoridor.Game()` is the classic game; `new Quoridor.Game('wallrush')` is a variant. Everything
else (wall rules, jumps, the "keep a path open" check, the board, the game screen, the computer's search) reads those numbers from
the game, so a new variant needs no new engine code. Snapshots carry a `variant` key; without one they are classic, so the server's
snapshots still load.

| Variant | Page | Board | Start | Goal |
|---|---|---|---|---|
| Wallrush | `/variants/wallrush/` | 9 columns x 13 rows, 10 walls each | both pawns on row 8 (columns 2 and 6) | both race to row 0 |
| Pointrush | `/variants/pointrush/` | 11 x 11, 2 to 4 players; 12, 8 or 6 walls each | middle of each edge (bottom, left, top, right), 5 squares from the centre | all race to the centre square (5,5) |
| Custom Game | `/variants/custom/` | square, 5 to 13 (odd), 0 to 30 walls each, chosen by the players | middle of the bottom and top rows | opposite row, as in classic |

Variants are played on one device only: the Python engine and the online server know only the classic game, so `tests/test_parity.py`
covers classic only. To add a variant: add its row to `VARIANTS`, give it a page like `wallrush()` in `pages.py` (a form with
`data-play-form="local" data-variant="<key>" data-leave="variants"`), and list it in `VARIANT_CARDS` so `/variants/` shows it.
Custom Game is the one variant that is not a fixed row: `new Quoridor.Game('custom', 2, {size, walls, borrow})` builds its row from
the options (`customOptions` checks them against `CUSTOM_LIMITS` and throws on anything else). The options are part of a snapshot
(`toJSON().options`), so `fromJSON`, `clone` and undo keep the setup; classic snapshots have no such key. The turn clock is not a
rule of the engine: `play.js` reads it from the form and passes `turnSeconds` to the game screen (`0` means no clock).
Pointrush is the variant for more than two players: `new Quoridor.Game('pointrush', n)` with `n` 2, 3 or 4 (`game.nPlayers`; every other
variant is two-player and refuses another count). Its row has `starts` for the four seats clockwise from the bottom, a `seats` map saying which
seats a game of `n` uses (2: bottom and top; 3: bottom, left, top; 4: all), and walls per player by count. Its goal is a single `goalCell`
instead of goal rows, so `distance()` and the win test look for that square. Turns pass in order (`(turn + 1) % nPlayers`, and
`moves[i]` belongs to player `i % nPlayers`); no one is ever eliminated. A pawn is never a destination: a jump needs the square behind the
pawn to be free, otherwise it side-steps, and a side-step square must be free too. A wall must leave a route for every pawn. Snapshots carry
`players` (missing means 2). The setup form (`players` radio buttons, `data-player-field` name fields) is read by `play.js`; the board draws
the four player colours (`PAWN_COLORS` in `board.js`) and rings the goal square. There is no computer opponent or online mode for it.
Screen names for squares and walls use the board's own height (`game.squareName`, `game.wallName`, `game.moveName`).

Coordinates (classic) are rows 0..8 from the top and columns 0..8 from the left. A wall `("h", r, c)` lies below row `r`
across columns `c` and `c+1`; `("v", r, c)` lies right of column `c` across rows `r` and `r+1` (`r`, `c` in 0..7).
Moves are `{type:"move", r, c}` or `{type:"wall", o:"h"|"v", r, c}`. Screen names: files a..i left to right, ranks
1..9 bottom to top; a wall is named after the square just below and left of its centre, plus its direction (`d4h`).

## Code map

| File | Role |
|---|---|
| `static/assets/js/engine.js` | Rules engine for the browser: legal moves, wall legality, shortest-path check, apply/undo, JSON snapshot |
| `server/engine.py` | The same rules in Python. The server uses this one; clients are never trusted |
| `static/assets/js/ai.js`, `ai-worker.js` | Computer opponent (four levels) and the worker that runs it off the main thread |
| `static/assets/js/board.js` | Accessible SVG board: drawing, mouse / touch / keyboard input. Only reports intent |
| `static/assets/js/game.js` | Game screen shared by all modes: turn bar, players, controls, move list, result |
| `static/assets/js/play.js` | Setup forms on the `/play/*` pages |
| `static/assets/js/online.js`, `room.js` | API client, long-poll session, and the `/room/<id>/` page |
| `server/rooms.py`, `server/api.py` | Rooms, matchmaking, presence, rate limits; HTTP/JSON routes (mounted by `serve.py`) |

The two engines must agree. `tests/test_parity.py` generates random games with the Python engine and replays them
through the JavaScript engine in headless Edge/Chrome, comparing pawn moves, the legality of all 128 wall slots,
and path lengths after every move (about 21,000 checks), plus undo and snapshot round-trips.

Known gap: a player whose only way out of a one-square-wide dead end is blocked by the opponent's pawn (with the jump
and side-steps walled off) has no legal pawn move; if they also have no walls left the game cannot continue. The published
rules don't say what happens then, and it is very unlikely in normal play, so the engine does not invent a rule.

## Computer opponent

All levels use one evaluation: (opponent's steps to goal minus your own) x 10, plus 2 per spare wall difference
(+1 for having the move). Candidate walls are limited to those that lengthen the opponent's current shortest route.

| Level | Search | Notes |
|---|---|---|
| Easy | own move only | heavy random noise; considers each candidate wall only 20% of the time |
| Medium | own move only | small noise |
| Hard | two plies (own move and the reply) | up to 14 candidate walls at the root, 10 deeper |
| Expert | iterative-deepening alpha-beta, up to 12 plies | 1 second (or 60,000 nodes) per move; reaches roughly depth 6 to 8 |

Details that matter for Expert's strength (each was found by watching games, see `tests/ai_game.html`):

* Only a finished *even* depth is trusted. An odd depth ends on the AI's own move, so its leaf scores are optimistic.
* Root moves are searched with a small window below the best score so that ties are scored exactly, and a tie is
  broken toward the move that leaves the AI's own route shortest.
* Stepping back onto a square it left in the last four moves costs 20 points. Without this, deep search saw nothing to
  choose between (it assumes the opponent answers every step with a perfect wall), the first-listed move won the tie
  and the pawn shuffled back and forth until the opponent walked home. That bug had Expert level with Hard (8-8) until
  fixed; afterwards Expert won 14 of 16.

**Measured strength** (`python tests/ai_bench.py 20 0`, robots against each other, colours alternating, Edge headless,
three games at a time on a 4-core PC, Expert on its real 1 s budget):

| Pairing | Result |
|---|---|
| Medium vs Easy | Medium won 17 of 20 |
| Hard vs Medium | Hard won 16 of 20 |
| Expert vs Hard | Expert won 16 of 20 |

Cost per move: Easy, Medium and Hard average 0.3 to 2 ms (worst about 0.2 s); Expert averaged 0.65 s, worst 1.02 s.
Expert's depth depends on the device: it stops when its second is up, so slow phones search shallower. Re-run the
benchmark after changing `ai.js` and update the descriptions on `/play/computer/` (`DIFFICULTY_LEVELS` in `pages.py`).

`python tests/ai_bench.py [games] [expert_nodes, 0 = real time] [pair ...]` runs the ladder. `tests/ai_speed.html` measures
nodes per second, `tests/ai_game.html` prints a full game with distances and walls, and `tests/ai_pos.html` shows the root
scores for one position (open them with the JSON arguments described in the file, or see how `ai_bench.py` drives them).

## Online protocol

JSON over HTTP, same origin, under `/api/` (see the docstring in `server/api.py` for every route). Clients send
intent (a move) and receive the resulting state; the server validates everything.

* **Identity.** A display name is not an identity. Joining returns a random seat token (header `X-Seat-Token`, never
  in a URL). The browser keeps it in `localStorage` under the room id so a reload or dropped connection rejoins the
  same seat.
* **Room ids** are 128-bit random (`secrets.token_urlsafe(16)`); the human **pairing code** is 6 characters from
  `ABCDEFGHJKLMNPQRSTUVWXYZ23456789`, valid only while the room waits for its second player.
* **Sync.** `GET /api/rooms/<id>/state?since=<version>` is a long poll (up to 25 s) that returns as soon as the room's
  version changes. Every change bumps the version; the response is a full snapshot.
* **Presence and forfeit.** A seat is connected while it has a poll in flight or polled in the last 15 s. A seat that
  is gone for 60 s forfeits (`reason: "disconnect"`); the opponent sees a countdown.
* **Clocks.** Each move must be made within 32 s (`TURN_SECONDS`, plus 1 s of grace), and each player also has 5 minutes for the
  whole game (`BANK_SECONDS`) that only runs on their own turn. When a move's 32 s run out the sweeper plays the pawn step that
  leaves the shortest route (`Game.timeout_move`) and charges the time to that player's bank. A player whose bank reaches zero loses
  (`reason: "timeout"`). A disconnected player's clock is held. The snapshot carries `turnLeft` (seconds, the smaller of the move
  limit and the bank) and `clocks` (each seat's bank in seconds, live for the player to move) for the on-screen clocks. Same-device
  and computer games run the same clocks in the browser (`game.js`).
* **Matchmaking.** `POST /api/queue` returns a ticket; `GET /api/queue/<ticket>` long-polls until matched, then returns
  the room id and seat token. Tickets not polled for 20 s are dropped.
* **Limits.** Per address, per minute: 10 room creations, 12 join attempts (code guessing), 15 searches, 240 moves.
  `QUORIDOR_TRUST_PROXY=1` makes the server read the client address from `X-Forwarded-For` (set it only behind a proxy
  you control).
* **Storage.** Everything is in memory. Restarting the server ends all games.
* **Rounds.** `snapshot.round` counts the games started in a room (1, then 2 after the first rematch ...). Together with the
  room id it names one game, which is how a browser counts a finished game once (see "Remembered name and scores").

## Remembered name and scores

`static/assets/js/profile.js` (`QuoridorProfile`) keeps two things in the browser's `localStorage`. Nothing in it is sent to the server.

| Entry | Holds | Used by |
|---|---|---|
| `quoridor.username` | the display name last used | `play.js` and `room.js` fill it into the name fields (on the one-device pages into Player 1) and save it when a valid name is submitted |
| `quoridor.scores` | `{pairs: [{id, names, wins, at}], seen: [game ids]}`: for each pair of names, the wins of each against the other | `game.js` counts a finished game and shows the line "Score: Ana 3 – 2 Ben" under the players |

A tally is by name (case-insensitive), not by account: a friend who plays under another name starts a new tally, and each browser tallies
the games it saw. A score is kept only for games between friends:

* a **private room** (the seat is saved with `via: 'private'` by `play.js`/`room.js`; matchmaking saves `via: 'match'` and keeps no score,
  because two strangers with the same name cannot be told apart), and
* a **one-device game of two** in which both players typed a name (`play.js` passes `scoreId` to `game.js`).

`game.js` counts a finished game once: `seen` holds the last 40 game ids (`<roomId>#<round>` online), so showing a result again (a reload, a
language change) never adds a second win. A player who leaves an online game in progress forfeits it; the opponent counts the win when the
result arrives, and `room.js` records the loss on the leaver's device before the seat is released. Storage that is blocked or full is
tolerated: the name is not remembered, and the tally then lives in memory until the page is closed. The Privacy Policy describes both entries
(`PROFILE_STORAGE_*` in `pages.py`); change it, and add an entry to `PRIVACY_HISTORY`, when this storage changes.

Timing constants live at the top of `server/rooms.py`.

## Running and testing

```powershell
python build.py                 # static site into ./public   (online pages say "coming soon")
$env:QUORIDOR_ONLINE=1; python build.py     # same, with the online modes switched on
python serve.py                 # http://localhost:8000, includes the /api server

python -m unittest tests.test_engine tests.test_rooms tests.test_http   # fast: rules, rooms, HTTP API
python -m unittest tests.test_parity                                    # JS engine == Python engine (needs Edge/Chrome)
python -m unittest tests.test_ui                                        # real-browser play-throughs of every mode
python check.py                                                         # site structure, SEO, links
```

`site.json` has `"online_server": false` by default so a static deployment never advertises modes it cannot run.
Set it to `true` only when the deployed site really is served by `serve.py` (or equivalent).
