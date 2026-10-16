"""Replays Python-generated games through the JavaScript engine in headless Edge/Chrome and
checks every position: pawn moves, wall legality (all 128 anchors), distances, undo.

Run: python -m unittest tests.test_parity     (skipped when no Edge/Chrome is installed)
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

ERR_CODE = {None: ".", "overlap": "o", "cross": "x", "blocks-path": "p", "no-walls": "n"}


def snapshot(g):
    d = g.to_dict()
    we = ""
    for o in ("h", "v"):
        for r in range(8):
            for c in range(8):
                we += ERR_CODE[g.wall_error(o, r, c)]
    dist = []
    for i in (0, 1):
        x = g.distance(i)
        dist.append(-1 if x is None else x)
    return {
        "pawns": d["pawns"], "turn": d["turn"], "winner": d["winner"], "wallsLeft": d["wallsLeft"],
        "pm": ";".join(sorted(f"{r},{c}" for r, c in g.pawn_moves())),
        "we": we, "d": dist,
    }


def random_move(g, rng, wall_bias):
    if g.walls_left[g.turn] > 0 and rng.random() < wall_bias:
        for _ in range(30):
            o, r, c = rng.choice("hv"), rng.randrange(8), rng.randrange(8)
            if g.wall_error(o, r, c) is None:
                return {"type": "wall", "o": o, "r": r, "c": c}
    r, c = rng.choice(g.pawn_moves())
    return {"type": "move", "r": r, "c": c}


def bad_moves(g, rng):
    out = []
    for _ in range(3):
        if rng.random() < 0.5:
            move = {"type": "move", "r": rng.randrange(-1, 10), "c": rng.randrange(-1, 10)}
        else:
            move = {"type": "wall", "o": rng.choice("hvx"), "r": rng.randrange(-1, 9), "c": rng.randrange(-1, 9)}
        probe = Game()
        probe.pawns, probe.h, probe.v = list(g.pawns), set(g.h), set(g.v)
        probe.walls_left, probe.turn, probe.winner = list(g.walls_left), g.turn, g.winner
        err = probe.apply(move)
        if err:
            out.append({"move": move, "err": err})
    return out


def make_games(n, seed):
    rng = random.Random(seed)
    games = []
    for _ in range(n):
        g = Game()
        wall_bias = rng.choice([0.2, 0.5, 0.8])
        game = {"start": snapshot(g), "steps": []}
        while g.winner is None and len(g.moves) < 160:
            move = random_move(g, rng, wall_bias)
            bad = bad_moves(g, rng)
            assert g.apply(move) is None
            game["steps"].append({"move": move, "bad": bad, "after": snapshot(g)})
        games.append(game)
    return games


class Parity(unittest.TestCase):
    @unittest.skipUnless(browser.find_browser(), "needs Edge or Chrome")
    def test_js_engine_matches_python_engine(self):
        gen = HERE / "_gen"
        gen.mkdir(exist_ok=True)
        games = make_games(40, seed=20240601)
        (gen / "fixtures.js").write_text("window.FIXTURES = " + json.dumps({"games": games}) + ";", encoding="utf-8")
        result = browser.result_json(browser.dump_dom(browser.file_url(HERE / "parity.html")))
        self.assertEqual(result["errors"], [])
        self.assertGreater(result["checks"], 3000)
        print(f"\nparity: {result['games']} games, {result['checks']} position checks")


if __name__ == "__main__":
    unittest.main()
