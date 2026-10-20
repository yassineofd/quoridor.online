"""Custom Game (the classic layout on a 5 to 13 square board, with the walls and borrowed moves the players choose) in the JavaScript engine.

Run: python -m unittest tests.test_custom     (skipped when no Edge/Chrome is installed)
"""

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from tests import browser  # noqa: E402


class Custom(unittest.TestCase):
    @classmethod
    @unittest.skipUnless(browser.find_browser(), "needs Edge or Chrome")
    def setUpClass(cls):
        cls.out = browser.result_json(browser.dump_dom(browser.file_url(HERE / "custom.html")))

    def setUp(self):
        if not browser.find_browser():
            self.skipTest("needs Edge or Chrome")

    def test_pawns_start_in_the_middle_of_opposite_edges_at_every_size(self):
        self.assertEqual(self.out["setups"], [
            "5 5 [[4,2],[0,2]] 0/4 10,10",
            "7 7 [[6,3],[0,3]] 0/6 10,10",
            "9 9 [[8,4],[0,4]] 0/8 10,10",
            "11 11 [[10,5],[0,5]] 0/10 10,10",
            "13 13 [[12,6],[0,6]] 0/12 10,10",
        ])

    def test_no_options_is_the_classic_game(self):
        self.assertEqual(self.out["defaultsMatchClassic"], "true,true,true,true,true")

    def test_walls_and_borrowed_moves_come_from_the_options(self):
        o = self.out
        self.assertEqual(o["options"], '3,3 true {"size":7,"walls":3,"borrow":true}')
        self.assertEqual(o["zeroWalls"], "no-walls")
        self.assertTrue(o["widestOk"])

    def test_only_supported_settings_are_accepted(self):
        self.assertEqual(self.out["badOptions"], "true,true,true,true,true,true,true,true")
        self.assertEqual(self.out["limits"], "0 30 5/7/9/11/13")

    def test_the_small_board_plays_like_the_classic_one(self):
        o = self.out
        self.assertEqual(o["smallJump"], "0,2;1,1;1,3;3,2")
        self.assertEqual(o["wallBounds"], ",out-of-bounds,out-of-bounds")
        self.assertEqual(o["win"], "0 game-over 0")

    def test_borrowed_moves_only_when_switched_on(self):
        self.assertEqual(self.out["borrowOff"], "2,4;4,3;5,4")
        self.assertEqual(self.out["borrowOn"], "2,4;3,3;4,3;5,4")

    def test_snapshots_and_undo_keep_the_setup(self):
        o = self.out
        self.assertEqual(o["snapshot"], "true 11 4,3 true 11")
        self.assertEqual(o["undo"], "4,4 1 11")
        self.assertTrue(o["classicHasNoOptions"])  # classic snapshots are unchanged, so the server's still load

    def test_square_names_cover_thirteen_files(self):
        self.assertEqual(self.out["names"], "m13,a1,l1v")


if __name__ == "__main__":
    unittest.main()
