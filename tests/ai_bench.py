"""Plays the computer levels against each other in headless Edge/Chrome and prints win counts.

Usage: python tests/ai_bench.py [games_per_pair] [expert_nodes, 0 = real 1 s budget] [pair ...]
       pair examples: easy:medium  medium:hard  hard:expert
Each game runs in its own browser process (a few at a time), so partial results appear as games finish
and one slow game cannot hold up the rest. These measured results are what the difficulty descriptions
on /play/computer/ are based on.
"""

import json
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from tests import browser  # noqa: E402

WORKERS = 3


def play_one(a, b, index, expert_nodes, max_plies):
    """One game: `a` moves first when index is even, else `b`. Returns (winner_level or None, plies, stats)."""
    first, second = (a, b) if index % 2 == 0 else (b, a)
    cfg = {"pairs": [[first, second]], "games": 1, "expertNodes": expert_nodes, "maxPlies": max_plies, "seedBase": 1000 + index, "realTime": expert_nodes == 0}
    url = browser.file_url(HERE / "ai.html") + "#" + urllib.parse.quote(json.dumps(cfg))
    res = browser.result_json(browser.dump_dom(url, budget_ms=0, timeout=1200))
    m = res["matches"][0]  # 'a' there is the side that moved first in this single game
    winner = first if m["aWins"] else second if m["bWins"] else None
    return winner, res["stats"]


def run(pairs, games, expert_nodes, max_plies=200):
    results = []
    with ThreadPoolExecutor(WORKERS) as pool:
        for a, b in pairs:
            futures = {pool.submit(play_one, a, b, i, expert_nodes, max_plies): i for i in range(games)}
            wins = {a: 0, b: 0, None: 0}
            stats = {}
            for fut in as_completed(futures):
                try:
                    winner, st = fut.result()
                except Exception as e:  # a stuck or crashed game is reported, not hidden
                    print("  game failed:", e, flush=True)
                    wins[None] += 1
                    continue
                wins[winner] += 1
                for lv, s in st.items():
                    t = stats.setdefault(lv, {"moves": 0, "avgMs": 0, "worst": 0, "walls": 0})
                    t["avgMs"] = round((t["avgMs"] * t["moves"] + s["avgMs"] * s["moves"]) / (t["moves"] + s["moves"]), 1)
                    t["moves"] += s["moves"]
                    t["worst"] = max(t["worst"], s["worst"])
                    t["walls"] += s.get("walls", 0)
                print(f"  {a} vs {b}: {wins[a]}-{wins[b]} (+{wins[None]} unfinished) after {sum(wins.values())} games", flush=True)
            results.append({"a": a, "b": b, "games": games, "aWins": wins[a], "bWins": wins[b], "unfinished": wins[None], "stats": stats})
    return results


if __name__ == "__main__":
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    nodes = int(sys.argv[2]) if len(sys.argv) > 2 else 0  # 0 = real time budget
    pairs = [p.split(":") for p in sys.argv[3:]] or [["easy", "medium"], ["medium", "hard"], ["hard", "expert"]]
    t0 = time.time()
    for m in run(pairs, games, nodes):
        print(f"{m['a']:>7} vs {m['b']:<7} {m['aWins']:>3} - {m['bWins']:<3} unfinished {m['unfinished']}  ({m['games']} games, colours alternate)")
        print("   per-move cost:", json.dumps(m["stats"]))
    print(f"{time.time() - t0:.0f}s")
