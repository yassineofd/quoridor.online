"""Achievements, score and rank (static/assets/js/achievements.js) in a real browser, through tests/achievements.html.

The page plays games with the real engine (static/assets/js/engine.js) and records them in an in-memory stand-in for
localStorage, so nothing depends on the browser's own storage. Skipped when no Edge/Chrome is installed.
Run: python -m unittest tests.test_achievements
"""

import json
import re
import socket
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from tests import browser  # noqa: E402

if browser.find_browser():
    from tests.cdp import Page

MESSAGES = json.loads((ROOT / "translations" / "js-en.json").read_text(encoding="utf-8"))


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@unittest.skipUnless(browser.find_browser(), "needs Edge or Chrome")
class Achievements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        page = Page(port=free_port())
        try:
            page.goto(browser.file_url(HERE / "achievements.html"), wait=1.0)
            page.wait_for("document.getElementById('result').textContent.length > 2", timeout=120)
            cls.out = json.loads(page.js("document.getElementById('result').textContent"))
            cls.console = list(page.console)
        finally:
            page.close()

    def test_the_page_ran_without_errors(self):
        self.assertEqual([c for c in self.console if c[0] in ("error", "exception")], [])

    # ---- the list ---------------------------------------------------------------------------
    def test_every_achievement_is_listed_once_with_points_an_icon_and_a_group(self):
        c = self.out["catalog"]
        self.assertTrue(c["unique"])
        self.assertTrue(c["allInACategory"])
        self.assertTrue(c["allPositive"])
        self.assertEqual(c["ranks"], "0,75,200,400,700,1100,1700")

    def test_every_text_the_page_needs_is_a_message_and_none_is_left_over(self):
        keys = set(self.out["catalog"]["keys"])
        self.assertEqual(sorted(k for k in keys if k not in MESSAGES), [], "messages missing from translations/js-en.json")
        listed = {m.group(1) for k in keys for m in [re.match(r"ach\.(\w+)\.(?:name|desc)$", k)] if m}
        left_over = [k for k in MESSAGES if (m := re.match(r"ach\.(\w+)\.(?:name|desc)$", k)) and m.group(1) not in listed]
        self.assertEqual(left_over, [], "messages for achievements that are not in CATALOG")

    def test_the_icons_exist(self):
        from lib import _ICONS
        js = (ROOT / "static" / "assets" / "js" / "achievements.js").read_text(encoding="utf-8")
        used = set(re.findall(r"(?:counter|event)\('\w+', '([\w-]+)'", js))
        self.assertTrue(used)
        self.assertEqual(sorted(used - set(_ICONS)), [])

    # ---- recording a game ---------------------------------------------------------------------
    def test_a_game_that_ends_almost_at_once_is_worth_nothing(self):
        self.assertEqual(self.out["short"], " 0")   # no result, and nothing was written to storage

    def test_a_first_win_earns_the_game_and_its_achievements(self):
        w = self.out["firstWin"]
        self.assertTrue(w["won"])
        self.assertEqual(w["ids"], "beatMedium,firstGame,firstWin,noWalls,speed")
        self.assertEqual(w["gained"], 20)    # 5 for playing, 10 for the win, 5 for beating the Medium robot
        self.assertEqual(w["bonus"], 155)    # 30 + 10 + 25 + 50 + 40
        self.assertEqual(w["total"], 175)
        self.assertEqual((w["score"], w["rank"], w["rankedUp"], w["saved"]), (175, 1, True, True))
        self.assertEqual(self.out["stored"], "1 1")

    def test_an_achievement_is_earned_once(self):
        s = self.out["second"]
        self.assertEqual((s["ids"], s["gained"], s["score"]), ("", 20, 195))

    def test_the_next_goal_is_the_one_furthest_along_and_never_a_trophy_count(self):
        self.assertEqual(self.out["goal"], "days3")

    def test_a_loss_still_counts_and_teaches(self):
        self.assertEqual(self.out["loss"], {"won": False, "gained": 5, "ids": "firstGame,learn"})

    def test_wins_in_a_row_are_counted_and_a_loss_ends_them(self):
        self.assertEqual(self.out["afterThree"], '[3,["winStreak3"]]')
        self.assertEqual(self.out["streakReset"], "3 wins 4")   # the best streak stays 3 after a loss and another win

    def test_days_in_a_row(self):
        d = self.out["days"]
        self.assertEqual(d["counted"], "1,2,3")
        self.assertTrue(d["unlockedDays3"])
        self.assertEqual(self.out["sameDay"], 3)                 # a second game the same day changes nothing
        self.assertEqual(self.out["skipped"], "1,3,1,0,3")      # skipping a day starts again at 1, the best stays 3, the streak is still alive the day after, gone two days after
        self.assertEqual(self.out["playedToday"], "true,false")

    def test_a_game_on_one_device_is_played_not_won(self):
        self.assertEqual(self.out["local"], {"won": None, "gained": 5, "ids": "firstGame,friend", "wins": 0})

    def test_each_variant_counts_towards_the_explorer(self):
        self.assertEqual(self.out["variants"].split(" | "), ["", "", "explorer"])
        self.assertEqual(self.out["explorerProgress"], "[3,3]")

    def test_online_games(self):
        self.assertEqual(self.out["online"], {"ids": "firstGame,firstWin,noWalls,onlineGame,onlineWin,speed", "gained": 35})
        self.assertEqual(self.out["onlineLoss"], {"won": False, "gained": 5})

    def test_a_win_by_the_other_side_giving_up_is_a_win_but_not_a_skill(self):
        self.assertEqual(self.out["onlineResign"], {"won": True, "ids": "firstGame,firstWin,onlineGame,onlineWin", "gained": 35})

    # ---- what the replay of a game finds ----------------------------------------------------------
    def test_a_jump_is_found_for_the_right_player(self):
        # [player 0 jumped, player 1 jumped, player 0's turns, player 0's walls, player 1's turns, player 1's walls, detour]
        self.assertEqual(self.out["jump"], "true false 5 1 4 0 0")

    def test_a_wall_that_closes_a_corridor_is_a_big_detour(self):
        # [detour, most steps behind, walls placed, walls left, detour of the other player, walls of the other player]
        self.assertEqual(self.out["detour"], "7 4 5 5 0 0")
        self.assertEqual(self.out["detourAchievement"], "detour,firstGame,firstWall,learn,onlineGame")

    def test_on_one_device_every_turn_counts_and_nothing_is_replayed(self):
        self.assertEqual(self.out["deviceCounts"], "9 5 false 0")

    def test_a_comeback_needs_five_steps_behind_and_a_win_at_the_goal(self):
        c = self.out["comeback"]
        self.assertEqual((c["winner"], c["behind"], c["walls"]), (0, 5, 5))
        self.assertTrue(c["achievement"])
        self.assertFalse(c["noWalls"])   # five walls were placed
        self.assertFalse(c["speed"])     # and it took more than 12 turns

    def test_using_every_wall_in_a_win(self):
        a = self.out["allWalls"]
        self.assertEqual((a["winner"], a["left"]), (0, 0))
        self.assertEqual(a["ids"], "allWalls,beatEasy,firstGame,firstWall,firstWin")

    # ---- the data in storage ---------------------------------------------------------------------
    def test_damaged_storage_starts_fresh_and_odd_values_are_made_safe(self):
        self.assertEqual(self.out["damaged"], "0 0")
        self.assertEqual(self.out["sane"], "10 0 3 1")   # score 10, 0 games, 3 wins (3.7 rounded down), 1 achievement; "bogus" and a negative score ignored

    def test_ranks_start_where_they_should(self):
        # rank index > points still needed for the next one; ">-" is the top rank
        self.assertEqual(self.out["ranks"], "0>75 0>1 1>125 1>1 2>200 5>1 6>- 6>-")
        self.assertEqual(json.loads(self.out["nextRank"]), {"rank": 2, "at": 200, "remaining": 100, "fraction": 0.2})

    def test_storage_that_refuses_to_save_still_works_until_the_page_closes(self):
        b = self.out["blocked"]
        self.assertEqual(b, {"saved": False, "score": True, "works": False})
        self.assertEqual(self.out["afterReset"], 0)

    def test_reset_removes_the_entry(self):
        self.assertTrue(self.out["works"])
        self.assertFalse(self.out["resetKey"])


if __name__ == "__main__":
    unittest.main()
