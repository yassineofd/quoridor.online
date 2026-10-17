"""End-to-end UI tests in a real (headless) browser against the real server.

Builds the site into a temp folder with online play enabled, starts serve.py on a spare port, and
drives local, computer and online (rooms + matchmaking) games through the page like a player would.
Skipped when no Edge/Chrome is installed.  Run: python -m unittest tests.test_ui -v
"""

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests import browser  # noqa: E402

if browser.find_browser():
    from tests.cdp import Page

SCREENSHOTS = os.environ.get("QUORIDOR_SHOTS")  # set to a folder to keep screenshots

SIZE, PAD, PITCH, CELL = 846, 16, 92, 78


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@unittest.skipUnless(browser.find_browser(), "needs Edge or Chrome")
class UI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="quoridor-ui-")
        env = dict(os.environ, QUORIDOR_ONLINE="1", QUORIDOR_BUILD_DIR=cls.tmp + "/site", QUORIDOR_PUBLIC=cls.tmp + "/site")
        subprocess.run([sys.executable, str(ROOT / "build.py")], cwd=ROOT, env=env, check=True, capture_output=True)
        cls.port = free_port()
        cls.log = open(cls.tmp + "/server.log", "w")
        cls.server = subprocess.Popen([sys.executable, str(ROOT / "serve.py"), str(cls.port)], cwd=ROOT, env=env,
                                      stdout=cls.log, stderr=subprocess.STDOUT)
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", cls.port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        cls.base = f"http://127.0.0.1:{cls.port}"
        # A second copy built the way the committed ./public is (online play off), as a static host would serve it.
        env2 = dict(os.environ, QUORIDOR_BUILD_DIR=cls.tmp + "/static", QUORIDOR_PUBLIC=cls.tmp + "/static")
        env2["QUORIDOR_ONLINE"] = "0"
        subprocess.run([sys.executable, str(ROOT / "build.py")], cwd=ROOT, env=env2, check=True, capture_output=True)
        cls.static_port = free_port()
        cls.static_server = subprocess.Popen([sys.executable, str(ROOT / "serve.py"), str(cls.static_port)], cwd=ROOT, env=env2,
                                             stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", cls.static_port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        cls.static_base = f"http://127.0.0.1:{cls.static_port}"
        cls.pages = []
        cls.next_debug_port = 9400

    @classmethod
    def tearDownClass(cls):
        cls.static_server.terminate()
        cls.static_server.wait(10)
        cls.server.terminate()
        cls.server.wait(10)
        cls.log.close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def tearDown(self):
        for p in self.pages:
            # A search still in the queue would match the next test's players: cancel it.
            try:
                p.js("(function(){var s=window.QuoridorOnline&&QuoridorOnline.loadSearch();"
                     "return s&&fetch(QuoridorOnline.root+'api/queue/'+s.ticket,{method:'DELETE'})})()")
                p.pump(0.3)
            except Exception:
                pass
            p.close()
        self.pages.clear()

    # ---- helpers --------------------------------------------------------------------
    def page(self, **kw):
        UI.next_debug_port += 1
        kw.setdefault("height", 1100)  # tall enough that the whole board is on screen for clicks
        p = Page(port=UI.next_debug_port, **kw)
        self.pages.append(p)
        return p

    def shot(self, p, name):
        if SCREENSHOTS:
            Path(SCREENSHOTS).mkdir(parents=True, exist_ok=True)
            p.screenshot(str(Path(SCREENSHOTS) / name))

    def no_errors(self, p):
        bad = [c for c in p.console if c[0] in ("error", "exception")]
        self.assertEqual(bad, [], f"console errors: {bad}")

    def board_xy(self, p, bx, by):
        left, top, width, height = p.js("(function(){var b=document.querySelector('svg.board').getBoundingClientRect();return [b.left,b.top,b.width,b.height]})()")
        flip = p.js("!!document.querySelector('svg.board > g[transform]')")
        if flip:
            bx, by = SIZE - bx, SIZE - by
        return left + bx * width / SIZE, top + by * height / SIZE

    def cell_xy(self, p, r, c):
        return self.board_xy(p, PAD + c * PITCH + CELL / 2, PAD + r * PITCH + CELL / 2)

    def wall_xy(self, p, o, r, c):
        ax, ay = PAD + c * PITCH + CELL + 7, PAD + r * PITCH + CELL + 7
        return self.board_xy(p, ax + (30 if o == "h" else 0), ay + (30 if o == "v" else 0))

    def click_cell(self, p, r, c):
        p.click_at(*self.cell_xy(p, r, c))

    def turn(self, p):
        return p.js("document.querySelector('.turn-bar').textContent")

    def hint(self, p):
        return p.js("document.querySelector('.game-hint').textContent")

    def moves(self, p):
        return p.js("document.querySelectorAll('.move-log li').length")

    def walls_left(self, p):
        return p.js("Array.from(document.querySelectorAll('.player-walls')).map(function(e){return e.textContent})")

    def start_local(self, p, n1="Alice", n2="Bob"):
        p.goto(self.base + "/play/local/")
        p.type_text("#name1", n1)
        p.type_text("#name2", n2)
        p.click("button[type=submit]")
        p.wait_for("document.querySelector('svg.board')")

    # ---- local ----------------------------------------------------------------------
    def test_local_pawn_moves_undo_and_turns(self):
        p = self.page()
        self.start_local(p)
        self.assertEqual(self.turn(p), "Alice's turn")
        self.click_cell(p, 5, 4)  # not a legal square: two steps away
        self.assertEqual(self.moves(p), 0)
        self.click_cell(p, 7, 4)
        self.assertEqual(self.turn(p), "Bob's turn")
        self.assertEqual(self.moves(p), 1)
        self.assertIn("Pass the device to Bob", self.hint(p))
        self.click_cell(p, 1, 4)
        self.assertEqual(self.turn(p), "Alice's turn")
        p.click(".game-controls .btn:nth-child(1)")  # Undo
        self.assertEqual(self.moves(p), 1)
        self.assertEqual(self.turn(p), "Bob's turn")
        self.no_errors(p)

    def test_local_wall_placement_with_mouse(self):
        p = self.page()
        self.start_local(p)
        self.shot(p, "local-start.png")
        p.click(".btn--toggle:nth-of-type(2)")
        self.assertEqual(p.js("document.querySelectorAll('.btn--toggle')[1].getAttribute('aria-pressed')"), "true")
        p.move_to(*self.wall_xy(p, "h", 6, 4))
        self.shot(p, "local-wall-preview.png")
        p.click_at(*self.wall_xy(p, "h", 6, 4))
        self.assertEqual(self.walls_left(p), ["Walls: 9", "Walls: 10"])
        self.assertEqual(self.turn(p), "Bob's turn")
        self.assertIn("placed wall e2h", p.js("document.querySelector('.move-log li').textContent"))
        # the wall now blocks Bob's... no: Alice's pawn can no longer step up? (wall is at rows 6/7, cols 4-5)
        # Bob tries the same slot: overlap
        p.click(".btn--toggle:nth-of-type(2)")
        p.click_at(*self.wall_xy(p, "h", 6, 4))
        self.assertIn("overlaps", self.hint(p))
        self.assertEqual(self.moves(p), 1)
        # a crossing wall is refused too
        p.click_at(*self.wall_xy(p, "v", 6, 4))
        self.assertIn("cross", self.hint(p))
        self.shot(p, "local-after-wall.png")
        self.no_errors(p)

    def test_walls_use_the_colour_of_the_player_who_placed_them(self):
        p = self.page()
        self.start_local(p)
        p.click(".btn--toggle:nth-of-type(2)")
        p.click_at(*self.wall_xy(p, "h", 6, 4))   # Alice (cyan pawn)
        p.click(".btn--toggle:nth-of-type(2)")
        p.click_at(*self.wall_xy(p, "h", 2, 1))   # Bob (orange pawn)
        fills = p.js("Array.from(document.querySelectorAll('svg.board g')).filter(function(g){return g.children.length===2 && g.children[0].getAttribute('rx')==='6'}).map(function(g){return Array.from(g.children).map(function(r){return r.getAttribute('fill')})})[0]")
        self.assertEqual(fills, ["#42d9f5", "#ff9f43"])
        self.no_errors(p)

    def test_local_turn_timer_counts_down_and_plays_when_time_is_up(self):
        p = self.page()
        self.start_local(p)
        self.assertRegex(p.js("document.querySelector('.turn-timer').textContent"), r"Alice: 1[45]s left")
        self.assertEqual(self.moves(p), 0)
        p.wait_for("document.querySelectorAll('.move-log li').length === 1", timeout=20)
        self.assertEqual(self.turn(p), "Bob's turn")
        self.assertIn("Time ran out. Alice moved to e2.", self.hint(p))
        self.assertRegex(p.js("document.querySelector('.turn-timer').textContent"), r"Bob: 1[45]s left")
        self.no_errors(p)

    def test_local_keyboard_play(self):
        p = self.page()
        self.start_local(p)
        p.js("document.querySelector('svg.board').focus()")
        p.key("ArrowUp")  # cursor starts on player 0's pawn at e1 -> e2
        p.key("Enter")
        self.assertEqual(self.moves(p), 1)
        self.assertEqual(self.turn(p), "Bob's turn")
        p.key("w")
        self.assertEqual(p.js("document.querySelectorAll('.btn--toggle')[1].getAttribute('aria-pressed')"), "true")
        for _ in range(3):
            p.key("ArrowDown")
        p.key("r")  # rotate to vertical
        p.key("Enter")
        self.assertEqual(self.moves(p), 2)
        self.assertEqual(self.walls_left(p), ["Walls: 10", "Walls: 9"])
        live = p.js("document.querySelector('[aria-live=polite].sr-only').textContent")
        self.assertIn("placed wall", live)
        self.no_errors(p)

    def test_local_play_to_a_win(self):
        p = self.page()
        self.start_local(p)
        p1 = [(7, 4), (6, 4), (5, 4), (4, 4), (3, 4), (2, 4), (1, 4), (0, 4)]
        p2 = [(0, 3), (0, 2), (0, 1), (0, 0), (1, 0), (2, 0), (3, 0)]
        for i, move in enumerate(p1):
            self.click_cell(p, *move)
            if i < len(p2):
                self.click_cell(p, *p2[i])
        self.assertEqual(self.turn(p), "Alice wins!")
        self.assertIn("Alice wins", p.js("document.querySelector('.result h2').textContent"))
        self.shot(p, "local-win.png")
        # the board is now read-only
        before = self.moves(p)
        self.click_cell(p, 4, 0)
        self.assertEqual(self.moves(p), before)
        # Play again returns to setup
        p.click(".result .btn--primary")
        self.assertTrue(p.js("!document.querySelector('[data-stage]').hidden"))
        self.no_errors(p)

    def test_local_rejects_bad_names(self):
        p = self.page()
        p.goto(self.base + "/play/local/")
        p.type_text("#name1", "<b>")
        p.click("button[type=submit]")
        self.assertFalse(p.js("document.querySelector('#name1-error').hidden"))
        self.assertTrue(p.js("document.querySelector('[data-game-wrap]').hidden"))

    # ---- computer -------------------------------------------------------------------
    def test_computer_replies_and_undo(self):
        for level in ("easy", "expert"):
            p = self.page()
            p.goto(self.base + "/play/computer/")
            p.click(f"label[for=d-{level}]")
            p.click("button[type=submit]")
            p.wait_for("document.querySelector('svg.board')")
            self.assertEqual(self.turn(p), "Your turn")
            self.click_cell(p, 7, 4)
            self.assertIn("thinking", self.turn(p))
            p.wait_for("document.querySelector('.turn-bar').textContent === 'Your turn'", timeout=15)
            self.assertEqual(self.moves(p), 2)
            self.shot(p, f"computer-{level}.png")
            p.click(".game-controls .btn:nth-child(1)")  # Undo takes back both plies
            self.assertEqual(self.moves(p), 0)
            self.assertEqual(self.turn(p), "Your turn")
            self.no_errors(p)
            p.close()
            self.pages.remove(p)

    def test_computer_resign(self):
        p = self.page()
        p.goto(self.base + "/play/computer/")
        p.click("button[type=submit]")
        p.wait_for("document.querySelector('svg.board')")
        self.click_cell(p, 7, 4)
        p.wait_for("document.querySelector('.turn-bar').textContent === 'Your turn'", timeout=15)
        p.js("window.confirm = function () { return true; }")
        p.click(".game-controls .btn:nth-child(2)")  # Resign
        self.assertIn("won", p.js("document.querySelector('.result h2').textContent"))
        self.assertIn("Medium robot", self.turn(p))
        self.no_errors(p)

    # ---- phone: touch + two-step wall placement ------------------------------------------
    def test_phone_layout_and_touch_wall(self):
        p = self.page(width=360, height=740, mobile=True, touch=True)
        self.start_local(p)
        self.assertFalse(p.js("document.documentElement.scrollWidth > document.documentElement.clientWidth"))
        self.shot(p, "phone-local.png")
        p.click(".btn--toggle:nth-of-type(2)")
        p.click_at(*self.wall_xy(p, "h", 6, 3))   # tap selects, does not place
        self.assertEqual(self.moves(p), 0)
        self.assertFalse(p.js("document.querySelector('.wall-row .btn--primary').disabled"))
        self.shot(p, "phone-wall-selected.png")
        p.click(".wall-row .btn--primary")        # confirm
        self.assertEqual(self.moves(p), 1)
        self.assertEqual(self.walls_left(p), ["Walls: 9", "Walls: 10"])
        self.assertFalse(p.js("document.documentElement.scrollWidth > document.documentElement.clientWidth"))
        self.no_errors(p)

    # ---- online: private room ------------------------------------------------------------
    def make_room(self, host, guest):
        host.goto(self.base + "/play/create-room/")
        host.type_text("#username", "Hana")
        host.click("button[type=submit]")
        host.wait_for("location.pathname.indexOf('/room/') === 0 && document.getElementById('invite-code').textContent.length === 6")
        code = host.js("document.getElementById('invite-code').textContent")
        link = host.js("document.getElementById('invite-link').textContent")
        guest.goto(self.base + "/play/join-room/")
        guest.type_text("#username", "Gus")
        guest.type_text("#code", code.lower())
        guest.click("button[type=submit]")
        for p in (host, guest):
            p.wait_for("document.querySelector('svg.board')", timeout=15)
        return code, link

    def test_private_room_full_game(self):
        host, guest = self.page(), self.page()
        code, link = self.make_room(host, guest)
        self.assertRegex(code, r"^[A-HJ-NP-Z2-9]{6}$")
        self.assertIn("/room/", link)
        self.no_errors(host)
        self.no_errors(guest)
        # exactly one of them is on move
        turns = [self.turn(host), self.turn(guest)]
        self.assertEqual(sorted(turns)[0], "Gus's turn" if "Gus's turn" in turns else "Hana's turn")
        mover, waiter = (host, guest) if self.turn(host) == "Your turn" else (guest, host)
        mover_is_host = mover is host
        self.shot(host, "room-host.png")
        self.shot(guest, "room-guest.png")
        # The second seat sees the board rotated so they are at the bottom.
        self.assertTrue(waiter.js("!!document.querySelector('svg.board > g[transform]')"))
        self.assertFalse(mover.js("!!document.querySelector('svg.board > g[transform]')"))
        # waiter cannot move
        self.click_cell(waiter, 1, 4)
        self.assertEqual(self.moves(waiter), 0)
        # mover steps forward, the opponent's page updates on its own
        self.click_cell(mover, 7, 4)
        waiter.wait_for("document.querySelectorAll('.move-log li').length === 1", timeout=10)
        waiter.wait_for("document.querySelector('.turn-bar').textContent === 'Your turn'", timeout=10)
        self.assertEqual(self.moves(mover), 1)
        # waiter replies with a wall, using the rotated board
        waiter.click(".btn--toggle:nth-of-type(2)")
        waiter.click_at(*self.wall_xy(waiter, "h", 6, 3))
        mover.wait_for("document.querySelectorAll('.move-log li').length === 2", timeout=10)
        self.assertEqual(self.moves(waiter), 2)
        # a page reload rejoins the same seat with the game intact
        mover.goto(mover.js("location.href"))
        mover.wait_for("document.querySelector('svg.board')", timeout=10)
        self.assertEqual(self.moves(mover), 2)
        self.assertEqual(self.turn(mover), "Your turn")
        # resign -> result and rematch for both
        mover.js("window.confirm = function () { return true; }")
        mover.click(".game-controls .btn:nth-child(1)")
        for p in (mover, waiter):
            p.wait_for("document.querySelector('.result') && !document.querySelector('.result').hidden", timeout=10)
        self.assertIn("won", waiter.js("document.querySelector('.result h2').textContent"))
        self.assertIn("resigned", waiter.js("document.querySelector('.result p').textContent"))
        self.shot(waiter, "room-result.png")
        mover.click(".result .btn--primary")
        waiter.wait_for("document.querySelector('.result p').textContent.indexOf('wants a rematch') > -1", timeout=10)
        waiter.click(".result .btn--primary")
        for p in (mover, waiter):
            p.wait_for("document.querySelectorAll('.move-log li').length === 0 && document.querySelector('.result').hidden", timeout=10)
        # seats swapped: whoever was waiting now moves first
        waiter.wait_for("document.querySelector('.turn-bar').textContent === 'Your turn'", timeout=10)
        self.no_errors(mover)
        self.no_errors(waiter)
        del mover_is_host

    def test_room_link_flow_and_errors(self):
        host, guest, late = self.page(), self.page(), self.page()
        host.goto(self.base + "/play/create-room/")
        host.type_text("#username", "Hana")
        host.click("button[type=submit]")
        host.wait_for("location.pathname.indexOf('/room/') === 0 && document.getElementById('invite-link').textContent.length > 10")
        link = host.js("document.getElementById('invite-link').textContent")
        self.shot(host, "room-waiting.png")
        guest.goto(link)
        guest.wait_for("!document.querySelector('[data-state=join]').hidden")
        self.assertIn("Hana", guest.js("document.getElementById('host-name').textContent"))
        guest.type_text("#username", "x")
        guest.click("[data-state=join] button[type=submit]")
        self.assertFalse(guest.js("document.getElementById('username-error').hidden"))
        guest.type_text("#username", "y")
        guest.click("[data-state=join] button[type=submit]")
        guest.wait_for("document.querySelector('svg.board')", timeout=15)
        host.wait_for("document.querySelector('svg.board')", timeout=15)
        # A third visitor sees "full"; an unknown room is "not available"; neither shows a board.
        late.goto(link)
        late.wait_for("!document.querySelector('[data-state=full]').hidden")
        late.goto(self.base + "/room/doesNotExist1234567890/")
        late.wait_for("!document.querySelector('[data-state=unavailable]').hidden")
        self.assertIsNone(late.js("document.querySelector('svg.board')"))
        # wrong code on the join page
        late.goto(self.base + "/play/join-room/")
        late.type_text("#username", "Zed")
        late.type_text("#code", "ZZZZZZ")
        late.click("button[type=submit]")
        late.wait_for("!document.querySelector('#code-error').hidden")
        self.assertIn("doesn't match", late.js("document.querySelector('#code-error').textContent"))

    def test_host_can_cancel_a_waiting_room(self):
        host = self.page()
        host.goto(self.base + "/play/create-room/")
        host.type_text("#username", "Hana")
        host.click("button[type=submit]")
        host.wait_for("document.getElementById('invite-code').textContent.length === 6")
        code = host.js("document.getElementById('invite-code').textContent")
        host.js("window.confirm = function () { return true; }")
        host.click("[data-state=waiting] [data-leave]")
        host.wait_for("!document.querySelector('[data-state=left]').hidden")
        guest = self.page()
        guest.goto(self.base + "/play/join-room/")
        guest.type_text("#username", "Gus")
        guest.type_text("#code", code)
        guest.click("button[type=submit]")
        guest.wait_for("!document.querySelector('#code-error').hidden")

    # ---- the static build (online play switched off) ----------------------------------------
    def test_static_build_is_honest_about_online_but_plays_offline_modes(self):
        p = self.page()
        p.goto(self.static_base + "/play/")
        text = p.js("document.querySelector('main').textContent")
        self.assertIn("Coming soon", text)
        # online and private-room forms validate, then say plainly that the feature isn't live
        p.goto(self.static_base + "/play/online/")
        p.type_text("#username", "Ann")
        p.click("button[type=submit]")
        self.assertFalse(p.js("document.querySelector('[data-unavailable]').hidden"))
        self.assertIsNone(p.js("document.querySelector('[data-searching]')"))
        p.goto(self.static_base + "/play/create-room/")
        p.type_text("#username", "Ann")
        p.click("button[type=submit]")
        self.assertFalse(p.js("document.querySelector('[data-unavailable]').hidden"))
        p.goto(self.static_base + "/room/abcdefghijklmnop/")
        self.assertFalse(p.js("document.querySelector('[data-state=unavailable]').hidden"))
        self.assertIn("aren't live yet", p.js("document.querySelector('[data-state=unavailable]').textContent"))
        # local and computer games need no server at all
        p.goto(self.static_base + "/play/local/")
        p.click("button[type=submit]")
        p.wait_for("document.querySelector('svg.board')")
        self.click_cell(p, 7, 4)
        self.assertEqual(self.moves(p), 1)
        self.no_errors(p)

    # ---- online: matchmaking -------------------------------------------------------------
    def test_matchmaking(self):
        a, b = self.page(), self.page()
        a.goto(self.base + "/play/online/")
        a.type_text("#username", "Ann")
        a.click("button[type=submit]")
        a.wait_for("!document.querySelector('[data-searching]').hidden")
        self.assertIn("Finding your opponent", a.js("document.querySelector('[data-search-text]').textContent"))
        self.assertRegex(a.js("document.querySelector('[data-search-elapsed]').textContent"), r"^\d\d:\d\d$")
        # the other ways to play stay hidden at first and list the computer before a friend
        self.assertTrue(a.js("document.querySelector('[data-slow]').hidden"))
        alts = a.js("Array.from(document.querySelectorAll('[data-alt]')).map(function(l){return l.getAttribute('href')}).join()").split(",")
        self.assertEqual([h.split("play/")[1] for h in alts], ["computer/", "create-room/"])
        self.shot(a, "online-searching.png")
        # cancelling returns to the form with the name kept
        a.click("[data-cancel-search]")
        self.assertTrue(a.js("document.querySelector('[data-searching]').hidden"))
        self.assertEqual(a.js("document.querySelector('#username').value"), "Ann")
        a.click("button[type=submit]")
        a.wait_for("!document.querySelector('[data-searching]').hidden")
        b.goto(self.base + "/play/online/")
        b.type_text("#username", "Bea")
        b.click("button[type=submit]")
        for p in (a, b):
            try:
                p.wait_for("document.querySelector('svg.board')", timeout=20)
            except AssertionError:
                state = p.js("location.pathname + ' | ' + Array.from(document.querySelectorAll('[data-searching],[data-error]')).map(function(e){return e.getAttribute('data-searching') !== null ? 'searching hidden=' + e.hidden : 'error hidden=' + e.hidden + ' ' + e.textContent}).join(' ; ')")
                extra = p.js("JSON.stringify({ready: document.readyState, online: typeof window.QuoridorOnline, engine: typeof window.Quoridor, game: typeof window.QuoridorGame, board: typeof window.QuoridorBoard, scripts: Array.from(document.scripts).map(function(x){return x.src.split('/').pop()}), res: performance.getEntriesByType('resource').filter(function(r){return /js$/.test(r.name)}).map(function(r){return r.name.split('/').pop() + ':' + r.responseStatus + ':' + r.transferSize})})")
                again = p.js("fetch('../../assets/js/online.js').then(function(r){return r.text()}).then(function(t){try{(0,eval)(t)}catch(e){return 'throws: ' + e + ' len=' + t.length}; return 'evaluated: ' + typeof window.QuoridorOnline + ' len=' + t.length})")
                self.fail(f"no game after matching: {state}; {extra}; reeval={again}; console={p.console}")
        names = sorted(a.js("Array.from(document.querySelectorAll('.player-name')).map(function(e){return e.textContent})"))
        self.assertEqual(names, ["Ann", "Bea"])
        self.no_errors(a)
        self.no_errors(b)

    # ---- online: a search that keeps running while the player plays the computer -------------
    def background_offer(self):
        """Ann searches, then moves on to the computer game; Bea searches. Returns (ann, bea)."""
        a, b = self.page(), self.page()
        a.goto(self.base + "/play/online/")
        a.type_text("#username", "Ann")
        a.click("button[type=submit]")
        a.wait_for("sessionStorage.getItem('quoridor.search')")        # the server has given us a ticket
        a.goto(self.base + "/play/computer/")             # leaves the search page; the search carries on
        a.wait_for("document.querySelector('.bg-search')")
        a.click("button[type=submit]")                    # Ann starts a game against the computer
        a.wait_for("document.querySelector('svg.board')")
        b.goto(self.base + "/play/online/")
        b.type_text("#username", "Bea")
        b.click("button[type=submit]")
        try:
            a.wait_for("document.querySelector('.match-offer')", timeout=15)
        except AssertionError:
            state = lambda p: p.js("location.pathname + ' | search=' + sessionStorage.getItem('quoridor.search') + ' | chip=' + ((document.querySelector('.bg-search')||{}).textContent) + ' | text=' + ((document.querySelector('[data-search-text]')||{}).textContent)")
            self.log.flush()
            tail = "\n".join(Path(self.tmp, "server.log").read_text().splitlines()[-40:])
            self.fail(f"no offer. ann: {state(a)} {a.console}; bea: {state(b)} {b.console}\n{tail}")
        return a, b

    def test_background_search_offers_the_match_mid_game(self):
        a, b = self.background_offer()
        self.assertIn("Bea", a.js("document.querySelector('.match-offer').textContent"))
        self.assertIn("ends the game", a.js("document.querySelector('.match-offer').textContent"))
        # Bea is told the other player still has to confirm, and is not dropped into a game
        b.wait_for("document.querySelector('[data-search-text]').textContent.indexOf('confirm') !== -1")
        self.assertIsNone(b.js("document.querySelector('svg.board')"))
        # Ann says yes: both land in the same online game
        a.click(".match-offer .btn--primary")
        for p in (a, b):
            p.wait_for("document.querySelector('svg.board') && location.pathname.indexOf('/room/') === 0", timeout=20)
        names = sorted(a.js("Array.from(document.querySelectorAll('.player-name')).map(function(e){return e.textContent})"))
        self.assertEqual(names, ["Ann", "Bea"])
        self.assertIsNone(a.js("document.querySelector('.bg-search')"))
        self.no_errors(a)
        self.no_errors(b)

    def test_declining_the_offer_keeps_the_computer_game_and_the_search(self):
        a, b = self.background_offer()
        a.click(".match-offer .btn--secondary")
        a.wait_for("!document.querySelector('.match-offer')")
        self.assertTrue(a.js("!!document.querySelector('svg.board') && location.pathname.indexOf('/play/computer') === 0"))
        self.assertTrue(a.js("!!document.querySelector('.bg-search')"))      # still searching in the background
        b.wait_for("document.querySelector('[data-search-text]').textContent.indexOf('confirm') === -1")
        self.assertIsNone(b.js("document.querySelector('svg.board')"))        # Bea goes on searching
        self.no_errors(a)

    def test_stopping_the_background_search(self):
        a, b = self.page(), self.page()
        a.goto(self.base + "/play/online/")
        a.type_text("#username", "Ann")
        a.click("button[type=submit]")
        a.wait_for("sessionStorage.getItem('quoridor.search')")
        a.goto(self.base + "/play/local/")
        a.wait_for("document.querySelector('.bg-search')")
        a.click(".bg-search button")
        a.wait_for("!document.querySelector('.bg-search')")
        self.assertIsNone(a.js("sessionStorage.getItem('quoridor.search')"))
        # nobody is left to match with
        b.goto(self.base + "/play/online/")
        b.type_text("#username", "Bea")
        b.click("button[type=submit]")
        time.sleep(2)
        self.assertFalse(b.js("document.querySelector('[data-searching]').hidden"))

    def test_search_page_picks_up_a_running_search_after_reload(self):
        a = self.page()
        a.goto(self.base + "/play/online/")
        a.type_text("#username", "Ann")
        a.click("button[type=submit]")
        a.wait_for("sessionStorage.getItem('quoridor.search')")
        a.goto(self.base + "/play/online/")
        a.wait_for("!document.querySelector('[data-searching]').hidden")
        self.assertEqual(a.js("document.querySelector('#username').value"), "Ann")


if __name__ == "__main__":
    unittest.main()
