"""Authoritative Quoridor rules engine: the classic game (two players, 9x9, 10 walls each) and its variants.

This is the server-side twin of static/assets/js/engine.js. The two implementations must agree
exactly; tests/test_parity.py replays Python-generated classic games through the JavaScript engine, and
tests/test_parity_variants.py does the same for every variant.

A variant is a board size, start squares, goals and a wall count (VARIANTS below). `Game()` is the classic game,
`Game("wallrush")` a variant, `Game("pointrush", 4)` a variant for 2 to 4 players, and
`Game("custom", 2, {"size": 7, "walls": 5})` a classic-style game whose board size, walls and borrowed moves the
players choose (see CUSTOM_LIMITS).

Coordinates: rows 0..rows-1 from the top, columns 0..cols-1 from the left.
  * classic: player 0 starts at (8, 4) and wins on row 0. Player 1 starts at (0, 4) and wins on row 8.
  * ("h", r, c): a horizontal wall lying below row r, covering columns c and c+1 (r in 0..rows-2, c in 0..cols-2).
  * ("v", r, c): a vertical wall lying right of column c, covering rows r and r+1 (same ranges).
Moves are plain dicts so they can travel as JSON:
  {"type": "move", "r": 7, "c": 4}   {"type": "wall", "o": "h", "r": 3, "c": 3}
"""

from collections import deque

SIZE = 9
WALLS_EACH = 10
START = ((8, 4), (0, 4))
GOAL_ROW = (0, 8)
DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))  # up, down, left, right: the order engine.js uses, which timeout_move() depends on

# The games this engine can play. `starts` and `goals` are per player; `walls` is how many each player gets.
#   borrow:    a pawn standing next to the opponent (no wall between them) may also move to any square the opponent
#              could reach from where it stands (two-player variants only).
#   goal_cell: instead of a goal row, every player races to this one square.
#   seats:     for a variant with more than two players: which of `starts` a game with that many players uses
#              (the first player always sits at the bottom). `walls` is then a number per player count.
VARIANTS = {
    "classic": {"rows": 9, "cols": 9, "starts": ((8, 4), (0, 4)), "goals": (0, 8), "walls": 10},
    "wallrush": {"rows": 13, "cols": 9, "starts": ((8, 2), (8, 6)), "goals": (0, 0), "walls": 10, "borrow": True},
    "pointrush": {"rows": 11, "cols": 11, "starts": ((10, 5), (5, 0), (0, 5), (5, 10)), "goal_cell": (5, 5),
                  "seats": {2: (0, 2), 3: (0, 1, 2), 4: (0, 1, 2, 3)}, "walls": {2: 12, 3: 8, 4: 6}},
}

# What the players of a custom game may choose, and what they get when they leave a setting out.
CUSTOM_LIMITS = {"sizes": (5, 7, 9, 11, 13), "min_walls": 0, "max_walls": 30, "size": 9, "walls": 10, "borrow": False}


def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def custom_options(options):
    """The setup of a custom game, checked: {"size", "walls", "borrow"}. Raises ValueError on a value outside CUSTOM_LIMITS."""
    options = {} if options is None else options
    if not isinstance(options, dict):
        raise ValueError("Custom options must be an object")
    lim = CUSTOM_LIMITS
    size, walls = options.get("size", lim["size"]), options.get("walls", lim["walls"])
    if not _is_int(size) or size not in lim["sizes"]:
        raise ValueError(f"Unsupported board size {size!r}")
    if not _is_int(walls) or not lim["min_walls"] <= walls <= lim["max_walls"]:
        raise ValueError(f"Unsupported wall count {walls!r}")
    return {"size": size, "walls": walls, "borrow": bool(options.get("borrow"))}


def _custom_variant(o):
    """The variant row for a custom game: the classic layout on a square board of the chosen size."""
    mid = (o["size"] - 1) // 2
    return {"rows": o["size"], "cols": o["size"], "starts": ((o["size"] - 1, mid), (0, mid)), "goals": (0, o["size"] - 1),
            "walls": o["walls"], "borrow": o["borrow"]}


def players_allowed(variant, players):
    """True if a game of this variant (a key of VARIANTS, or "custom") can be played by this many players."""
    if not _is_int(players):
        return False
    if variant == "custom":
        return players == 2
    row = VARIANTS.get(variant) if isinstance(variant, str) else None
    if row is None:
        return False
    return players in row["seats"] if "seats" in row else players == 2


class Game:
    def __init__(self, variant=None, players=None, options=None):
        name = "classic" if variant is None else variant
        self.options = None
        if name == "custom":
            self.options = custom_options(options)
            v = _custom_variant(self.options)
        elif isinstance(name, str) and name in VARIANTS:
            v = VARIANTS[name]
        else:
            raise ValueError(f"Unknown variant {name!r}")
        n = 2 if players is None else players
        if not players_allowed(name, n):
            raise ValueError(f"Variant {name} cannot be played by {n!r} players")
        seats = v["seats"][n] if "seats" in v else (0, 1)
        walls = v["walls"] if _is_int(v["walls"]) else v["walls"][n]
        self.variant = name
        self.rows, self.cols = v["rows"], v["cols"]
        self.n_players = n
        self.goals = list(v["goals"]) if "goals" in v else [None] * n
        self.goal_cell = v.get("goal_cell")
        self.borrow = bool(v.get("borrow"))
        self.pawns = [v["starts"][s] for s in seats]
        self.h = set()
        self.v = set()
        self.walls_left = [walls] * n
        self.turn = 0
        self.winner = None
        self.moves = []  # every applied move, in order, as the dicts that were submitted

    # ---- geometry -------------------------------------------------------------------
    def in_bounds(self, r, c):
        return 0 <= r < self.rows and 0 <= c < self.cols

    def blocked(self, r, c, dr, dc):
        """True if a wall lies between (r, c) and its neighbour (r+dr, c+dc)."""
        if dr == 1:
            return (r, c) in self.h or (r, c - 1) in self.h
        if dr == -1:
            return (r - 1, c) in self.h or (r - 1, c - 1) in self.h
        if dc == 1:
            return (r, c) in self.v or (r - 1, c) in self.v
        return (r, c - 1) in self.v or (r - 1, c - 1) in self.v

    def _occupied(self, r, c):
        return (r, c) in self.pawns

    def _moves_from(self, me):
        """Legal destinations of a pawn standing on `me`, jumps included, and whether another pawn is next to it
        with no wall between them. No pawn is ever a destination: a jump needs the square behind the pawn to be
        free, otherwise the pawn side-steps, to a free square."""
        out, adjacent = [], False
        r, c = me
        for dr, dc in DIRS:
            nr, nc = r + dr, c + dc
            if not self.in_bounds(nr, nc) or self.blocked(r, c, dr, dc):
                continue
            if not self._occupied(nr, nc):
                out.append((nr, nc))
                continue
            adjacent = True
            jr, jc = nr + dr, nc + dc
            if self.in_bounds(jr, jc) and not self.blocked(nr, nc, dr, dc) and not self._occupied(jr, jc):
                out.append((jr, jc))
                continue
            # Straight jump blocked by a wall, the edge or another pawn: step beside the pawn instead.
            for sr, sc in DIRS:
                if (sr, sc) in ((dr, dc), (-dr, -dc)):
                    continue
                tr, tc = nr + sr, nc + sc
                if self.in_bounds(tr, tc) and not self.blocked(nr, nc, sr, sc) and not self._occupied(tr, tc):
                    out.append((tr, tc))
        return out, adjacent

    def pawn_moves(self, player=None):
        """Legal destination squares for a pawn, including jumps. In a `borrow` variant a pawn next to the
        opponent also gets the opponent's own moves."""
        p = self.turn if player is None else player
        out, adjacent = self._moves_from(self.pawns[p])
        if adjacent and self.borrow:
            me = self.pawns[p]
            extra, _ = self._moves_from(self.pawns[1 - p])
            for t in extra:
                if t != me and t not in out:
                    out.append(t)
        return out

    # ---- paths ----------------------------------------------------------------------
    def _at_goal(self, player, r, c):
        return (r, c) == self.goal_cell if self.goal_cell is not None else r == self.goals[player]

    def distance(self, player, start=None):
        """Shortest number of pawn steps to the goal (a row, or the goal square). Only walls count as obstacles.
        Returns None if no route exists. `start` tries another square instead of the pawn's own."""
        start = self.pawns[player] if start is None else start
        if self._at_goal(player, *start):
            return 0
        seen = {start}
        queue = deque([(start, 0)])
        while queue:
            (r, c), d = queue.popleft()
            for dr, dc in DIRS:
                nr, nc = r + dr, c + dc
                if not self.in_bounds(nr, nc) or (nr, nc) in seen or self.blocked(r, c, dr, dc):
                    continue
                if self._at_goal(player, nr, nc):
                    return d + 1
                seen.add((nr, nc))
                queue.append(((nr, nc), d + 1))
        return None

    # ---- walls ----------------------------------------------------------------------
    def wall_error(self, o, r, c, player=None):
        """None if the current player may place this wall now, else a short reason code."""
        p = self.turn if player is None else player
        if o not in ("h", "v") or not (0 <= r <= self.rows - 2 and 0 <= c <= self.cols - 2):
            return "out-of-bounds"
        if self.walls_left[p] <= 0:
            return "no-walls"
        same, other = (self.h, self.v) if o == "h" else (self.v, self.h)
        step = (0, 1) if o == "h" else (1, 0)
        if (r, c) in same or (r - step[0], c - step[1]) in same or (r + step[0], c + step[1]) in same:
            return "overlap"
        if (r, c) in other:
            return "cross"
        same.add((r, c))
        try:
            # A wall must leave a route for every pawn (pawns themselves are ignored by that check).
            if any(self.distance(i) is None for i in range(self.n_players)):
                return "blocks-path"
        finally:
            same.discard((r, c))
        return None

    # ---- applying moves -------------------------------------------------------------
    def apply(self, move):
        """Apply a move for the player to move. Returns None on success, else a reason code."""
        if self.winner is not None:
            return "game-over"
        if not isinstance(move, dict):
            return "bad-move"
        kind = move.get("type")
        p = self.turn
        if kind == "move":
            r, c = move.get("r"), move.get("c")
            if not _is_int(r) or not _is_int(c) or (r, c) not in self.pawn_moves(p):
                return "illegal-move"
            self.pawns[p] = (r, c)
            self.moves.append({"type": "move", "r": r, "c": c})
            if self._at_goal(p, r, c):
                self.winner = p
        elif kind == "wall":
            o, r, c = move.get("o"), move.get("r"), move.get("c")
            if not _is_int(r) or not _is_int(c):
                return "bad-move"
            err = self.wall_error(o, r, c, p)
            if err:
                return err
            (self.h if o == "h" else self.v).add((r, c))
            self.walls_left[p] -= 1
            self.moves.append({"type": "wall", "o": o, "r": r, "c": c})
        else:
            return "bad-move"
        if self.winner is None:
            self.turn = (p + 1) % self.n_players
        return None

    def timeout_move(self):
        """The move played for the player to move when their time runs out: the pawn step that
        leaves the shortest route to the goal. None if the pawn has no step at all."""
        p = self.turn
        steps = self.pawn_moves(p)
        if not steps:
            return None
        best = min(steps, key=lambda sq: self.distance(p, sq))
        return {"type": "move", "r": best[0], "c": best[1]}

    def resign(self, player):
        """The player gives up: the next player in turn order is the winner (with two players, the other one)."""
        if self.winner is None:
            self.winner = (player + 1) % self.n_players

    # ---- serialisation --------------------------------------------------------------
    def to_dict(self):
        out = {
            "variant": self.variant,
            "players": self.n_players,
            "pawns": [list(p) for p in self.pawns],
            "walls": [["h", r, c] for r, c in sorted(self.h)] + [["v", r, c] for r, c in sorted(self.v)],
            "wallsLeft": list(self.walls_left),
            "turn": self.turn,
            "winner": self.winner,
            "moves": list(self.moves),
        }
        if self.options is not None:
            out["options"] = dict(self.options)
        return out
