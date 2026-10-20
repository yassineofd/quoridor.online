"""Wallrush lets a pawn next to the opponent also use the opponent's moves; classic does not.

Run: python -m unittest tests.test_borrow     (skipped when no Edge/Chrome is installed)
"""

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from tests import browser  # noqa: E402


class Borrow(unittest.TestCase):
    @unittest.skipUnless(browser.find_browser(), "needs Edge or Chrome")
    def test_wallrush_borrows_the_adjacent_opponents_moves(self):
        out = browser.result_json(browser.dump_dom(browser.file_url(HERE / "borrow.html")))
        # own moves 4,3 6,3 5,2 and the jump 5,5; borrowed 4,4 and 6,4
        self.assertEqual(out["adjacent"], "4,3;4,4;5,2;5,5;6,3;6,4")
        self.assertEqual(out["theirTurn"], "4,3;4,4;5,2;5,5;6,3;6,4")
        self.assertEqual(out["diagonal"], "4,3;5,2;5,4;6,3")  # diagonal is not adjacent
        self.assertEqual(out["walled"], "4,3;5,2;6,3")        # a wall between the pawns ends it
        self.assertEqual(out["classic"], "2,4;4,3;4,5;5,4")   # classic rules are unchanged


if __name__ == "__main__":
    unittest.main()
