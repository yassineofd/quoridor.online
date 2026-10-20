"""Pointrush (2 to 4 players, one goal square in the middle of an 11 x 11 board) in the JavaScript engine.

Run: python -m unittest tests.test_pointrush     (skipped when no Edge/Chrome is installed)
"""

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from tests import browser  # noqa: E402


class Pointrush(unittest.TestCase):
    @classmethod
    @unittest.skipUnless(browser.find_browser(), "needs Edge or Chrome")
    def setUpClass(cls):
        cls.out = browser.result_json(browser.dump_dom(browser.file_url(HERE / "pointrush.html")))

    def setUp(self):
        if not browser.find_browser():
            self.skipTest("needs Edge or Chrome")

    def test_setup_for_two_three_and_four_players(self):
        o = self.out
        self.assertEqual(o["setup2"], "2 11 11 [[10,5],[0,5]] 12,12")
        self.assertEqual(o["setup3"], "3 11 11 [[10,5],[5,0],[0,5]] 8,8,8")
        self.assertEqual(o["setup4"], "4 11 11 [[10,5],[5,0],[0,5],[5,10]] 6,6,6,6")
        self.assertEqual(o["defaultPlayers"], 2)
        self.assertEqual(o["classicPlayers"], 2)

    def test_only_supported_player_counts_are_accepted(self):
        self.assertEqual(self.out["badCounts"], "true,true,true,true")

    def test_turns_pass_in_order_and_wrap(self):
        self.assertEqual(self.out["turnAfter5"], 2)
        self.assertEqual(self.out["moveOwners"], "01201")

    def test_pawns_are_jumped_but_never_landed_on(self):
        o = self.out
        self.assertEqual(o["plain"], "5,5;6,4;6,6;7,5")
        self.assertEqual(o["jump"], "5,5;6,4;6,6;8,5")
        self.assertEqual(o["jumpBlockedByPawn"], "5,5;6,4;6,6;7,4;7,6")
        self.assertEqual(o["walled"], "5,5;6,4;6,6")

    def test_first_pawn_on_the_center_square_wins(self):
        o = self.out
        self.assertEqual(o["winner"], 0)
        self.assertEqual(o["afterWin"], "game-over")
        self.assertEqual(o["winnerDistance"], 0)

    def test_no_pawn_may_be_shut_in(self):
        self.assertEqual(self.out["sealed"], "blocks-path")
        self.assertIsNone(self.out["openWall"])
        self.assertEqual(self.out["distances"], "10,5")

    def test_snapshots_and_undo_keep_every_player(self):
        o = self.out
        self.assertEqual(o["snapshot"], "3 3 3 1 true")
        self.assertEqual(o["undo"], "2 [[9,5],[5,0],[0,5]] 8,7,8")
        self.assertEqual(o["classicSnapshot"], 2)  # a snapshot without a player count is a two-player game

    def test_square_names_cover_eleven_files(self):
        self.assertEqual(self.out["names"], "f6,k1,j1h")


if __name__ == "__main__":
    unittest.main()
