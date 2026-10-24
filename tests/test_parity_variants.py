"""The variants of the Python engine (server/engine.py) against the JavaScript engine (static/assets/js/engine.js).

Random games are played with the Python engine for Wallrush, Pointrush (2, 3 and 4 players) and Custom games
of several shapes. Every position is replayed through the JavaScript engine in headless Edge/Chrome and compared:
the full snapshot, the pawn moves of every player, the legality of wall slots, the distances, the move played when
a clock runs out, and the way bad moves are refused. Undo is checked on the way back.

Run: python -m unittest tests.test_parity_variants     (skipped when no Edge/Chrome is installed)
"""

import json
import random
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from server.engine import Game  # noqa: E402
from tests import browser  # noqa: E402

ERR_CODE = {None: ".", "overlap": "o", "cross": "x", "blocks-path": "p", "no-walls": "n", "out-of-bounds": "b"}

# (variant, players, options, games, wall grid checked every n steps, crowded positions)
CONFIGS = [
    ("classic", 2, None, 2, 3, 40),
    ("wallrush", 2, None, 4, 3, 80),
    ("pointrush", 2, None, 3, 4, 40),
    ("pointrush", 3, None, 4, 4, 120),
    ("pointrush", 4, None, 4, 4, 160),
    ("custom", 2, {"size": 5, "walls": 3, "borrow": False}, 3, 2, 40),
    ("custom", 2, {"size": 7, "walls": 8, "borrow": True}, 3, 3, 80),
    ("custom", 2, {"size": 9, "walls": 0, "borrow": True}, 2, 2, 20),
    ("custom", 2, {"size": 13, "walls": 30, "borrow": False}, 2, 6, 20),
]


def snapshot(g, grid):
    we = None
    if grid:
        we = ""
        for o in ("h", "v"):
            for r in range(g.rows - 1):
                for c in range(g.cols - 1):
                    we += ERR_CODE[g.wall_error(o, r, c)]
    return {
        "json": g.to_dict(),
        "pm": [";".join(sorted(f"{r},{c}" for r, c in g.pawn_moves(p))) for p in range(g.n_players)],
        "we": we,
        "d": [-1 if g.distance(p) is None else g.distance(p) for p in range(g.n_players)],
        "tm": g.timeout_move(),
    }


def random_move(g, rng, wall_bias, converge=0.0):
    if g.walls_left[g.turn] > 0 and rng.random() < wall_bias:
        for _ in range(30):
            o, r, c = rng.choice("hv"), rng.randrange(g.rows - 1), rng.randrange(g.cols - 1)
            if g.wall_error(o, r, c) is None:
                return {"type": "wall", "o": o, "r": r, "c": c}
    moves = g.pawn_moves()
    if not moves:
        return None
    if rng.random() < converge:   # head for the goal: with a shared goal square this packs the pawns together
        r, c = min(moves, key=lambda sq: g.distance(g.turn, sq))
    else:
        r, c = rng.choice(moves)
    return {"type": "move", "r": r, "c": c}


def bad_moves(g, rng, variant, players, options):
    out = []
    for _ in range(3):
        if rng.random() < 0.5:
            move = {"type": "move", "r": rng.randrange(-1, g.rows + 1), "c": rng.randrange(-1, g.cols + 1)}
        else:
            move = {"type": "wall", "o": rng.choice("hvx"), "r": rng.randrange(-1, g.rows), "c": rng.randrange(-1, g.cols)}
        probe = Game(variant, players, options)
        probe.pawns, probe.h, probe.v = list(g.pawns), set(g.h), set(g.v)
        probe.walls_left, probe.turn, probe.winner = list(g.walls_left), g.turn, g.winner
        err = probe.apply(move)
        if err:
            out.append({"move": move, "err": err})
    return out


def crowded_position(variant, players, options, rng):
    """A position nobody would reach by playing: a few random walls, then every pawn squeezed into a small window
    (so pawns stand next to each other, three in a line, in corners ...). Tests the rules about meeting pawns."""
    g = Game(variant, players, options)
    for _ in range(rng.randrange(0, 14)):
        for _ in range(20):
            o, r, c = rng.choice("hv"), rng.randrange(g.rows - 1), rng.randrange(g.cols - 1)
            if g.wall_error(o, r, c) is None and g.apply({"type": "wall", "o": o, "r": r, "c": c}) is None:
                break
    for _ in range(50):   # walls may legally close off an empty pocket: a pawn put there would have no route, so try again
        r0, c0 = rng.randrange(g.rows - 2), rng.randrange(g.cols - 2)
        squares = [(r0 + dr, c0 + dc) for dr in range(3) for dc in range(3)]
        rng.shuffle(squares)
        g.pawns = squares[:players]
        if all(g.distance(p) is not None for p in range(players)):
            break
    else:
        g = Game(variant, players, options)
    g.turn = rng.randrange(players)
    return g


def make_config(variant, players, options, n_games, every, crowded, seed):
    rng = random.Random(seed)
    positions = []
    for i in range(crowded):
        g = crowded_position(variant, players, options, rng)
        positions.append({"snap": snapshot(g, i % 5 == 0)})
    games = []
    for _ in range(n_games):
        g = Game(variant, players, options)
        wall_bias = rng.choice([0.1, 0.2, 0.5, 0.8])
        converge = rng.choice([0.0, 0.7, 0.95])
        game = {"start": snapshot(g, True), "steps": []}
        while g.winner is None and len(g.moves) < 140:
            move = random_move(g, rng, wall_bias, converge)
            if move is None:   # a pawn with no step and no wall to place: the engine's documented gap
                break
            bad = bad_moves(g, rng, variant, players, options)
            assert g.apply(move) is None
            game["steps"].append({"move": move, "bad": bad, "after": snapshot(g, len(g.moves) % every == 0 or g.winner is not None)})
        games.append(game)
    return {"variant": variant, "players": players, "options": options, "games": games, "positions": positions}


class VariantParity(unittest.TestCase):
    @unittest.skipUnless(browser.find_browser(), "needs Edge or Chrome")
    def test_js_engine_matches_python_engine_for_every_variant(self):
        from tests.cdp import Page

        gen = HERE / "_gen"
        gen.mkdir(exist_ok=True)
        configs = [make_config(*cfg, seed=20261024 + i) for i, cfg in enumerate(CONFIGS)]
        (gen / "fixtures_variants.js").write_text("window.FIXTURES = " + json.dumps({"configs": configs}) + ";", encoding="utf-8")
        page = Page(port=9371)
        try:
            page.goto(browser.file_url(HERE / "parity_variants.html"), wait=0.2)
            page.wait_for("document.getElementById('result').textContent !== 'running'", timeout=240)
            result = json.loads(page.js("document.getElementById('result').textContent"))
        finally:
            page.close()
        self.assertEqual(result["errors"], [])
        self.assertGreater(result["checks"], 3000)
        print(f"\nvariant parity: {result['games']} games, {result['checks']} position checks")


if __name__ == "__main__":
    unittest.main()
