"""Tournaments in a real (headless) browser: the stands on the home, Play and Variants pages, signing up, being taken to a match,
the game screen of a tournament match and the way back. Skipped when no Edge/Chrome is installed.

The server runs in this process (like tests/test_http.py) so the test can move the tournaments' clock to a start time.
Run: python -m unittest tests.test_tournaments_ui -v
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests import browser  # noqa: E402

if browser.find_browser():
    from tests.cdp import Page

SCREENSHOTS = os.environ.get("QUORIDOR_SHOTS")  # set to a folder to keep screenshots


@unittest.skipUnless(browser.find_browser(), "needs Edge or Chrome")
class TournamentUI(unittest.TestCase):
    next_port = 9650

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="quoridor-tour-")
        env = dict(os.environ, QUORIDOR_ONLINE="1", QUORIDOR_BUILD_DIR=cls.tmp + "/site")
        subprocess.run([sys.executable, str(ROOT / "build.py")], cwd=ROOT, env=env, check=True, capture_output=True)
        import serve
        from server import api
        cls.api = api
        cls.serve = serve
        cls.old_public = serve.PUBLIC
        serve.PUBLIC = Path(cls.tmp) / "site"
        class Quiet(serve.Server):
            def handle_error(self, request, client_address):   # (a browser that closes with a long poll open is not an error)
                pass

        cls.httpd = Quiet(("127.0.0.1", 0), serve.Handler)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        serve.Handler.log_message = lambda *a, **k: None
        cls.pages = []

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.serve.PUBLIC = cls.old_public
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def setUp(self):
        self.api.hub.__init__()                     # fresh tournaments
        self.now = [time.time()]
        self.api.hub.tournaments.clock = lambda: self.now[0]
        self.api.hub.start_sweeper()
        self.n = 0

    def tearDown(self):
        for p in self.pages:
            p.close()
        self.pages.clear()

    # ---- helpers --------------------------------------------------------------------
    def page(self, **kw):
        TournamentUI.next_port += 1
        kw.setdefault("height", 1000)
        p = Page(port=TournamentUI.next_port, **kw)
        self.pages.append(p)
        return p

    def shot(self, p, name):
        if SCREENSHOTS:
            Path(SCREENSHOTS).mkdir(parents=True, exist_ok=True)
            p.screenshot(str(Path(SCREENSHOTS) / name))

    def call(self, method, path, body=None, token=None):
        req = urllib.request.Request(self.base + "/api" + path, data=json.dumps(body).encode() if body is not None else None, method=method)
        if token:
            req.add_header("X-Seat-Token", token)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            return json.loads(e.read())

    def open_tournament(self, size):
        listing = self.call("GET", "/tournaments")
        return next(t for t in listing["tournaments"] if t["size"] == size and t["status"] == "open")

    def sign_up_others(self, tid, count, prefix="Rival"):
        """`count` more players sign up through the API; returns {name: token}."""
        out = {}
        for _ in range(count):
            self.n += 1
            name = f"{prefix} {self.n}"
            res = self.call("POST", f"/tournaments/{tid}/join", {"username": name})
            self.assertIn("token", res, res)
            out[name] = res["token"]
            self.api.hub.hits.clear()              # (several sign-ups from one address in a test are not abuse)
        return out

    def no_errors(self, p):
        bad = [c for c in p.console if c[0] in ("error", "exception")]
        self.assertEqual(bad, [], f"console errors: {bad}")

    def start_now(self, tournament):
        self.now[0] = tournament["start"] + 1.0
        self.api.hub.tournaments.sweep()

    # ---- the stands -------------------------------------------------------------------
    def test_a_stand_on_the_home_play_and_variants_pages(self):
        p = self.page()
        for path in ("/", "/play", "/variants"):
            p.goto(self.base + path)
            p.wait_for("document.querySelector('.tournament-strip')")
            text = p.js("document.querySelector('.tournament-strip').textContent")
            self.assertIn("Play in a Quoridor tournament", text, path)
            self.assertIn("8 or 16 players", text, path)
            hrefs = p.js("Array.from(document.querySelectorAll('.tournament-strip a')).map(function(a){return a.getAttribute('href')})")
            self.assertTrue(any(h.endswith("/tournaments") for h in hrefs), (path, hrefs))
            self.assertTrue(any(h.endswith("/tournaments#how") for h in hrefs), (path, hrefs))
            # The live line comes from the server: when the next one starts and how many places are taken.
            p.wait_for("document.querySelector('[data-tour-live]') && !document.querySelector('[data-tour-live]').hidden")
            line = p.js("document.querySelector('[data-tour-live]').textContent")
            self.assertIn("Next tournament:", line, path)
            self.assertIn("Places taken: 0 of 8 and 0 of 16", line, path)
        self.no_errors(p)

    def test_the_stand_follows_the_language_and_the_sign_ups(self):
        tid = self.open_tournament(8)["id"]
        self.sign_up_others(tid, 3)
        p = self.page()
        p.goto(self.base + "/?lang=es")
        p.wait_for("document.querySelector('[data-tour-live]') && !document.querySelector('[data-tour-live]').hidden")
        self.assertIn("Plazas ocupadas: 3 de 8 y 0 de 16", p.js("document.querySelector('[data-tour-live]').textContent"))
        self.assertIn("Juega en un torneo de Quoridor", p.js("document.querySelector('.tournament-strip h3').textContent"))
        self.no_errors(p)

    # ---- the page ---------------------------------------------------------------------
    def test_the_page_lists_both_sizes_and_signs_a_player_up(self):
        p = self.page()
        p.goto(self.base + "/tournaments")
        p.wait_for("document.querySelectorAll('[data-tour-upcoming] .tour-card').length === 2")
        titles = p.js("Array.from(document.querySelectorAll('[data-tour-upcoming] .tour-card__title')).map(function(e){return e.textContent})")
        self.assertEqual(titles, ["8-player tournament", "16-player tournament"])
        self.assertIn("0 of 8 players signed up", p.js("document.querySelector('.tour-card__seats').textContent"))
        self.assertRegex(p.js("document.querySelector('.tour-card__left').textContent"), r"in \d+:\d\d")
        self.shot(p, "tournaments-open.png")

        # a bad name is refused in the page
        p.type_text(".tour-card input", "x")
        p.click(".tour-card button[type=submit]")
        self.assertIn("2 to 20 characters", p.js("document.querySelector('.tour-card .field-error').textContent"))
        # a good one signs the player up
        p.js("document.querySelector('.tour-card input').value=''")
        p.type_text(".tour-card input", "Zoë")
        p.click(".tour-card button[type=submit]")
        p.wait_for("document.querySelector('.tour-card__in')")
        self.assertIn("You are signed up as", p.js("document.querySelector('.tour-card__in').textContent"))
        self.assertIn("1 of 8 players signed up", p.js("document.querySelector('.tour-card__seats').textContent"))
        self.assertIn("Zoë", p.js("document.querySelector('.tour-names').textContent"))
        self.shot(p, "tournaments-signed-up.png")
        tid = self.open_tournament(8)["id"]
        self.assertIsNotNone(p.js(f"localStorage.getItem('quoridor.tour.{tid}')"))

        # the entry survives a reload, and the same name cannot be taken twice
        p.goto(self.base + "/tournaments")
        p.wait_for("document.querySelector('.tour-card__in')")
        other = self.call("POST", f"/tournaments/{tid}/join", {"username": "zoë"})
        self.assertEqual(other["error"], "name-taken")

        # the stand elsewhere reminds the player for a moment
        p.goto(self.base + "/play")
        p.wait_for("document.querySelector('.tour-chip')")
        self.assertIn("You are signed up for the tournament that starts", p.js("document.querySelector('.tour-chip').textContent"))

        # withdrawing takes the name off the list
        p.goto(self.base + "/tournaments")
        p.wait_for("document.querySelector('.tour-card__in')")
        p.js("window.confirm=function(){return true}")
        p.click(".tour-card__in-row button")
        p.wait_for("document.querySelector('.tour-card input')")
        self.assertIn("0 of 8 players signed up", p.js("document.querySelector('.tour-card__seats').textContent"))
        self.assertIsNone(p.js(f"localStorage.getItem('quoridor.tour.{tid}')"))
        self.no_errors(p)

    def test_a_name_being_typed_survives_a_new_language_and_a_new_list(self):
        p = self.page()
        p.goto(self.base + "/tournaments")
        p.wait_for("document.querySelector('.tour-card input')")
        p.type_text(".tour-card input", "Bea")
        # someone else signs up and the page is told (the list is read again): the card is kept as it is
        tid = self.open_tournament(8)["id"]
        self.sign_up_others(tid, 1)
        p.js("document.querySelector('[data-retry]').click()")        # (the same call as the page's regular refresh)
        p.wait_for("document.querySelector('.tour-card__seats').textContent.indexOf('1 of 8') !== -1")
        self.assertEqual(p.js("document.querySelector('.tour-card input').value"), "Bea")
        self.assertTrue(p.js("document.activeElement === document.querySelector('.tour-card input')"))   # still where the cursor was
        # a change of language writes the form again in that language and keeps the text
        p.goto(self.base + "/tournaments")
        p.wait_for("document.querySelector('.tour-card input')")
        p.type_text(".tour-card input", "Bea")
        p.js("QuoridorI18n.setLanguage('es')")
        p.wait_for("document.querySelector('.tour-card button[type=submit]') && document.querySelector('.tour-card button[type=submit]').textContent.indexOf('Inscribirme') !== -1")
        self.assertEqual(p.js("document.querySelector('.tour-card input').value"), "Bea")
        self.assertIn("Torneo de 8 jugadores", p.js("document.querySelector('.tour-card__title').textContent"))
        self.assertIn("Empieza", p.js("document.querySelector('.tour-card__when').textContent"))
        self.no_errors(p)

    def test_the_page_reads_right_to_left_in_arabic(self):
        p = self.page()
        p.goto(self.base + "/tournaments?lang=ar")
        p.wait_for("document.querySelector('.tour-card input')")
        self.assertEqual(p.js("document.documentElement.dir"), "rtl")
        self.assertIn("بطولة 8 لاعبًا", p.js("document.querySelector('.tour-card__title').textContent"))
        self.assertLessEqual(p.js("document.documentElement.scrollWidth"), p.js("window.innerWidth"))
        self.shot(p, "tournaments-arabic.png")
        self.no_errors(p)

    def test_a_full_tournament_has_no_form(self):
        tid = self.open_tournament(8)["id"]
        self.sign_up_others(tid, 8)
        p = self.page()
        p.goto(self.base + "/tournaments")
        p.wait_for("document.querySelector('.tour-card__seats')")
        self.assertIn("8 of 8 players signed up", p.js("document.querySelector('.tour-card__seats').textContent"))
        self.assertIn("This tournament is full", p.js("document.querySelector('.tour-card__foot').textContent"))
        self.assertEqual(p.js("document.querySelectorAll('.tour-card')[0].querySelectorAll('input').length"), 0)

    def test_a_cancelled_tournament_is_listed_as_such(self):
        t = self.open_tournament(8)
        self.sign_up_others(t["id"], 5)
        self.start_now(t)
        p = self.page()
        p.goto(self.base + "/tournaments")
        p.wait_for("document.querySelector('[data-tour-recent] .tour-card')")
        text = p.js("document.querySelector('[data-tour-recent]').textContent")
        self.assertIn("Cancelled: only 5 of 8 players signed up.", text)
        self.assertEqual(p.js("document.querySelectorAll('[data-tour-upcoming] .tour-card').length"), 2)   # the next start is open
        self.no_errors(p)

    # ---- playing it -------------------------------------------------------------------
    def test_from_signing_up_to_the_next_round(self):
        t = self.open_tournament(8)
        others = self.sign_up_others(t["id"], 7)
        p = self.page()
        p.goto(self.base + "/tournaments")
        p.wait_for("document.querySelector('.tour-card input')")
        p.type_text(".tour-card input", "Ana")
        p.click(".tour-card button[type=submit]")
        p.wait_for("document.querySelector('.tour-card__in')")
        self.assertIn("8 of 8 players signed up", p.js("document.querySelector('.tour-card__seats').textContent"))

        self.start_now(t)                           # the start time comes: the bracket is drawn
        p.wait_for("document.querySelector('.tour-you--match')", timeout=20)
        banner = p.js("document.querySelector('.tour-you').textContent")
        self.assertIn("Your match against", banner)
        self.assertIn("Quarterfinal", banner)
        self.shot(p, "tournaments-match-ready.png")

        # the page takes the player to the game; it is a match of a tournament
        p.wait_for("document.querySelector('svg.board')", timeout=20)
        self.assertIn("/room/", p.js("location.pathname"))
        self.assertIn("Tournament · Quarterfinal", p.js("document.querySelector('.tour-line').textContent"))
        p.wait_for("document.querySelector('.player-name')")
        names = p.js("Array.from(document.querySelectorAll('.player-name')).map(function(e){return e.textContent})")
        self.assertIn("Ana", names)
        opponent = next(n for n in names if n != "Ana")
        self.assertIn(opponent, others)
        self.shot(p, "tournaments-game.png")

        # the opponent gives up; the result leads back to the tournament and offers no rematch
        match = self.call("GET", f"/tournaments/{t['id']}", token=others[opponent])["you"]["match"]
        self.call("POST", f"/rooms/{match['roomId']}/resign", token=match["token"])
        p.wait_for("document.querySelector('.result:not([hidden])')", timeout=20)
        self.assertIn("You won", p.js("document.querySelector('.result').textContent"))
        buttons = p.js("Array.from(document.querySelectorAll('.result .btn')).map(function(e){return e.textContent.trim()})")
        self.assertIn("Back to the tournament", buttons)
        self.assertFalse([b for b in buttons if "ematch" in b], buttons)
        self.shot(p, "tournaments-game-won.png")
        p.click(".result a.btn--primary")
        p.wait_for("document.querySelector('.tour-you')", timeout=20)
        self.assertIn("You are through to the next round", p.js("document.querySelector('.tour-you').textContent"))
        self.assertIn("/tournaments", p.js("location.pathname"))

        # the bracket shows the result
        p.wait_for("document.querySelector('.bracket')", timeout=20)
        self.assertEqual(p.js("document.querySelectorAll('.bracket-round').length"), 3)
        self.assertEqual(p.js("Array.from(document.querySelectorAll('.bracket-round h4')).map(function(e){return e.textContent})"),
                         ["Quarterfinal", "Semifinal", "Final"])
        self.assertIn("Ana", p.js("document.querySelector('.bracket-player.is-winner').textContent"))
        self.shot(p, "tournaments-bracket.png")
        self.no_errors(p)

    def test_a_player_who_never_opens_the_match_forfeits_it(self):
        t = self.open_tournament(8)
        others = self.sign_up_others(t["id"], 8)
        self.start_now(t)
        names = list(others)
        view = self.call("GET", f"/tournaments/{t['id']}", token=others[names[0]])
        match = view["you"]["match"]
        # this player opens the match; the opponent never does
        room_token, room_id = match["token"], match["roomId"]
        self.call("GET", f"/rooms/{room_id}/state", token=room_token)
        rooms = self.api.hub.rooms[room_id]
        for seat in rooms.seats:
            if seat.token != room_token:
                seat.lost_at = time.monotonic() - 1000
        self.api.hub.sweep()
        view = self.call("GET", f"/tournaments/{t['id']}", token=others[names[0]])
        self.assertEqual(view["you"]["state"], "in")
        done = view["bracket"][0][match["slot"]]
        self.assertEqual((done["state"], done["by"]), ("done", "walkover"))
        p = self.page()
        p.goto(self.base + "/tournaments?t=" + t["id"])
        p.wait_for("document.querySelector('.bracket')", timeout=20)
        self.assertIn("walkover", p.js("document.querySelector('.bracket').textContent"))

    # ---- small screens ----------------------------------------------------------------------
    def test_nothing_overflows_a_phone(self):
        t = self.open_tournament(16)
        self.sign_up_others(t["id"], 16, prefix="Alexandrina-Maria")
        p = self.page(width=360, height=740, mobile=True)
        p.goto(self.base + "/tournaments")
        p.wait_for("document.querySelector('.tour-card__seats')")
        self.assertLessEqual(p.js("document.documentElement.scrollWidth"), 360)
        self.start_now(t)
        p.goto(self.base + "/tournaments?t=" + t["id"])
        p.wait_for("document.querySelector('.bracket')", timeout=20)
        self.assertLessEqual(p.js("document.documentElement.scrollWidth"), 360)
        self.assertEqual(p.js("document.querySelectorAll('.bracket-round').length"), 4)
        self.shot(p, "tournaments-phone-bracket.png")
        for path in ("/", "/play", "/variants"):
            p.goto(self.base + path)
            p.wait_for("document.querySelector('.tournament-strip')")
            self.assertLessEqual(p.js("document.documentElement.scrollWidth"), 360, path)
        self.no_errors(p)


if __name__ == "__main__":
    unittest.main()
