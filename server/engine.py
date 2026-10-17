"""Authoritative Quoridor rules engine (two players, 9x9, 10 walls each).

This is the server-side twin of static/assets/js/engine.js. The two implementations must agree
exactly; tests/test_parity.py replays Python-generated games through the JavaScript engine.

Coordinates: rows 0..8 from the top, columns 0..8 from the left.
  * Player 0 starts at (8, 4) and wins on row 0. Player 1 starts at (0, 4) and wins on row 8.
  * ("h", r, c): a horizontal wall lying below row r, covering columns c and c+1 (r, c in 0..7).
  * ("v", r, c): a vertical wall lying right of column c, covering rows r and r+1 (r, c in 0..7).
Moves are plain dicts so they can travel as JSON:
  {"type": "move", "r": 7, "c": 4}   {"type": "wall", "o": "h", "r": 3, "c": 3}
"""

from collections import deque

SIZE = 9
WALLS_EACH = 10
START = ((8, 4), (0, 4))
GOAL_ROW = (0, 8)
DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def in_bounds(r, c):
    return 0 <= r < SIZE and 0 <= c < SIZE


class Game:
    def __init__(self):
        self.pawns = [START[0], START[1]]
        self.h = set()
        self.v = set()
        self.walls_left = [WALLS_EACH, WALLS_EACH]
        self.turn = 0
        self.winner = None
        self.moves = []  # every applied move, in order, as the dicts that were submitted

    # ---- geometry -------------------------------------------------------------------
    def blocked(self, r, c, dr, dc):
        """True if a wall lies between (r, c) and its neighbour (r+dr, c+dc)."""
        if dr == 1:
            return (r, c) in self.h or (r, c - 1) in self.h
        if dr == -1:
            return (r - 1, c) in self.h or (r - 1, c - 1) in self.h
        if dc == 1:
            return (r, c) in self.v or (r - 1, c) in self.v
        return (r, c - 1) in self.v or (r - 1, c - 1) in self.v

    def pawn_moves(self, player=None):
        """Legal destination squares for a pawn, including jumps."""
        p = self.turn if player is None else player
        r, c = self.pawns[p]
        orr, oc = self.pawns[1 - p]
        out = []
        for dr, dc in DIRS:
            nr, nc = r + dr, c + dc
            if not in_bounds(nr, nc) or self.blocked(r, c, dr, dc):
                continue
            if (nr, nc) != (orr, oc):
                out.append((nr, nc))
                continue
            jr, jc = nr + dr, nc + dc
            if in_bounds(jr, jc) and not self.blocked(nr, nc, dr, dc):
                out.append((jr, jc))
                continue
            # Straight jump blocked by a wall or the edge: step beside the opponent instead.
            for sr, sc in DIRS:
                if (sr, sc) in ((dr, dc), (-dr, -dc)):
                    continue
                tr, tc = nr + sr, nc + sc
                if in_bounds(tr, tc) and not self.blocked(nr, nc, sr, sc):
                    out.append((tr, tc))
        return out

    # ---- paths ----------------------------------------------------------------------
    def distance(self, player, start=None):
        """Shortest number of pawn steps to the goal row. Only walls count as obstacles.
        Returns None if no route exists. `start` tries another square instead of the pawn's own."""
        start = self.pawns[player] if start is None else start
        goal = GOAL_ROW[player]
        if start[0] == goal:
            return 0
        seen = {start}
        queue = deque([(start, 0)])
        while queue:
            (r, c), d = queue.popleft()
            for dr, dc in DIRS:
                nr, nc = r + dr, c + dc
                if not in_bounds(nr, nc) or (nr, nc) in seen or self.blocked(r, c, dr, dc):
                    continue
                if nr == goal:
                    return d + 1
                seen.add((nr, nc))
                queue.append(((nr, nc), d + 1))
        return None

    # ---- walls ----------------------------------------------------------------------
    def wall_error(self, o, r, c, player=None):
        """None if the current player may place this wall now, else a short reason code."""
        p = self.turn if player is None else player
        if o not in ("h", "v") or not (0 <= r <= 7 and 0 <= c <= 7):
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
            if self.distance(0) is None or self.distance(1) is None:
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
            if r == GOAL_ROW[p]:
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
            self.turn = 1 - p
        return None

    def timeout_move(self):
        """The move played for the player to move when their time runs out: the pawn step that
        leaves the shortest route to the goal."""
        p = self.turn
        best = min(self.pawn_moves(p), key=lambda sq: self.distance(p, sq))
        return {"type": "move", "r": best[0], "c": best[1]}

    def resign(self, player):
        if self.winner is None:
            self.winner = 1 - player

    # ---- serialisation --------------------------------------------------------------
    def to_dict(self):
        return {
            "pawns": [list(p) for p in self.pawns],
            "walls": [["h", r, c] for r, c in sorted(self.h)] + [["v", r, c] for r, c in sorted(self.v)],
            "wallsLeft": list(self.walls_left),
            "turn": self.turn,
            "winner": self.winner,
            "moves": list(self.moves),
        }


def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)
