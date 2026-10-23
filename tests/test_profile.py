"""The remembered name and the tally of wins between two friends (static/assets/js/profile.js).

Run: python -m unittest tests.test_profile     (skipped when no Edge/Chrome is installed)
"""

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from tests import browser  # noqa: E402


class Profile(unittest.TestCase):
    @unittest.skipUnless(browser.find_browser(), "needs Edge or Chrome")
    def test_name_and_tally(self):
        out = browser.result_json(browser.dump_dom(browser.file_url(HERE / "profile.html")))
        self.assertEqual(out["nameStart"], "")
        self.assertEqual(out["nameSaved"], "Hana")
        self.assertIsNone(out["none"])
        self.assertEqual(out["first"], [1, 0])
        self.assertEqual(out["sameGameAgain"], [1, 0])
        self.assertEqual(out["otherWay"], [0, 1])
        self.assertEqual(out["swapped"], [1, 1])
        self.assertEqual(out["caseless"], [2, 1])
        self.assertEqual(out["pairs"], 1)
        self.assertEqual(out["spelling"], "ana+BEN")
        self.assertIsNone(out["sameName"])
        self.assertIsNone(out["badWinner"])
        self.assertEqual(out["after"], [2, 1])

    @unittest.skipUnless(browser.find_browser(), "needs Edge or Chrome")
    def test_limits_damage_and_blocked_storage(self):
        out = browser.result_json(browser.dump_dom(browser.file_url(HERE / "profile.html")))
        self.assertEqual(out["kept"], 50)
        self.assertEqual(out["newest"], [1, 0])
        self.assertIsNone(out["oldest"])
        self.assertEqual(out["seen"], 40)
        self.assertEqual(out["damaged"], [0, 2])           # nonsense entries are skipped, a bad number counts as 0
        self.assertIsNone(out["garbage"])
        self.assertEqual(out["memory"], [0, 1])          # Yan won: counted although nothing could be saved
        self.assertEqual(out["nameWhenBlocked"], "Hana")  # the name that was saved before stays; nothing new is saved


if __name__ == "__main__":
    unittest.main()
