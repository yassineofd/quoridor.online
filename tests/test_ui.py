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

    def pick_wall(self, p, o):
        """Tap the wall of this type in the tray (the tap-then-place way of placing a wall)."""
        p.click(f'.wall-chip[data-o="{o}"]')

    def chip_xy(self, p, o):
        x, y, _, _ = p.center(f'.wall-chip[data-o="{o}"]')
        return x, y

    def clocks(self, p):
        return p.js("Array.from(document.querySelectorAll('.player-clock')).map(function(e){return e.textContent})")

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
        self.pick_wall(p, "h")
        self.assertEqual(p.js("document.querySelector('.wall-chip[data-o=h]').getAttribute('aria-pressed')"), "true")
        p.move_to(*self.wall_xy(p, "h", 6, 4))
        self.shot(p, "local-wall-preview.png")
        p.click_at(*self.wall_xy(p, "h", 6, 4))
        self.assertEqual(self.walls_left(p), ["Walls: 9", "Walls: 10"])
        self.assertEqual(self.turn(p), "Bob's turn")
        self.assertIn("placed wall e2h", p.js("document.querySelector('.move-log li').textContent"))
        # the wall now blocks Bob's... no: Alice's pawn can no longer step up? (wall is at rows 6/7, cols 4-5)
        # Bob tries the same slot: overlap
        self.pick_wall(p, "h")
        p.click_at(*self.wall_xy(p, "h", 6, 4))
        self.assertIn("overlaps", self.hint(p))
        self.assertEqual(self.moves(p), 1)
        # a crossing wall is refused too
        self.pick_wall(p, "v")
        p.click_at(*self.wall_xy(p, "v", 6, 4))
        self.assertIn("cross", self.hint(p))
        self.shot(p, "local-after-wall.png")
        self.no_errors(p)

    # ---- Wallrush (a variant: 13 rows x 9 columns, both pawns start on row 8 and race to row 0) ----
    WR_W, WR_H = PAD * 2 + 9 * CELL + 8 * (PITCH - CELL), PAD * 2 + 13 * CELL + 12 * (PITCH - CELL)

    def wr_xy(self, p, bx, by):
        left, top, width, height = p.js("(function(){var b=document.querySelector('svg.board').getBoundingClientRect();return [b.left,b.top,b.width,b.height]})()")
        return left + bx * width / self.WR_W, top + by * height / self.WR_H

    def wr_cell(self, p, r, c):
        return self.wr_xy(p, PAD + c * PITCH + CELL / 2, PAD + r * PITCH + CELL / 2)

    def start_wallrush(self, p, n1="Alice", n2="Bob"):
        p.goto(self.base + "/variants/wallrush/")
        self.shot(p, "wallrush-page.png")
        p.type_text("#name1", n1)
        p.type_text("#name2", n2)
        p.click("button[type=submit]")
        p.wait_for("document.querySelector('svg.board')")

    def test_wallrush_board_start_and_race_to_the_top(self):
        p = self.page(height=1400)  # tall enough for the whole 13-row board
        self.start_wallrush(p)
        self.assertEqual(p.js("document.querySelectorAll('svg.board rect[fill=\"#111c30\"]').length"), 13 * 9)
        self.assertEqual(p.js("document.querySelector('svg.board').getAttribute('viewBox')"), f"0 0 {self.WR_W} {self.WR_H}")
        self.shot(p, "wallrush-start.png")
        self.assertEqual(self.turn(p), "Alice's turn")
        self.assertEqual(self.walls_left(p), ["Walls: 10", "Walls: 10"])
        self.click_cell_wr = lambda r, c: p.click_at(*self.wr_cell(p, r, c))
        self.click_cell_wr(6, 2)      # two steps away: refused
        self.assertEqual(self.moves(p), 0)
        for r in range(7, -1, -1):    # Alice (first to move) reaches row 0 one move before Bob
            self.click_cell_wr(r, 2)
            if r > 0:
                self.assertEqual(self.turn(p), "Bob's turn")
                self.click_cell_wr(r, 6)
        self.assertIn("Alice wins", self.turn(p))
        self.assertEqual(self.moves(p), 15)
        self.assertTrue(p.js("document.querySelector('.result a.btn[href$=\"variants\"]') !== null"))
        self.no_errors(p)

    def test_wallrush_walls_can_be_placed_in_the_lowest_row(self):
        p = self.page(height=1400)
        self.start_wallrush(p)
        self.pick_wall(p, "h")
        # the lowest wall slot: below row 11, across columns 3 and 4
        p.click_at(*self.wr_xy(p, PAD + 3 * PITCH + CELL + 7 + 30, PAD + 11 * PITCH + CELL + 7))
        self.assertEqual(self.walls_left(p), ["Walls: 9", "Walls: 10"])
        self.assertIn("placed wall d1h", p.js("document.querySelector('.move-log li').textContent"))
        self.no_errors(p)

    # ---- Pointrush (a variant: 11 x 11, two to four players, everybody races to the center square) ----
    PR = PAD * 2 + 11 * CELL + 10 * (PITCH - CELL)

    def pr_click(self, p, r, c):
        left, top, width, height = p.js("(function(){var b=document.querySelector('svg.board').getBoundingClientRect();return [b.left,b.top,b.width,b.height]})()")
        p.click_at(left + (PAD + c * PITCH + CELL / 2) * width / self.PR, top + (PAD + r * PITCH + CELL / 2) * height / self.PR)

    def test_pointrush_with_four_players_everyone_races_to_the_center(self):
        p = self.page()
        p.goto(self.base + "/variants/pointrush/")
        self.shot(p, "pointrush-page.png")
        # two players to begin with: only the first two name fields show
        self.assertEqual(p.js("document.querySelector('#players-2').checked"), True)
        self.assertEqual(p.js("[1,2,3,4].map(function(n){return document.querySelector('[data-player-field=\"'+n+'\"]').hidden}).join()"), "false,false,true,true")
        p.js("document.querySelector('#players-4').click()")
        self.assertEqual(p.js("[1,2,3,4].map(function(n){return document.querySelector('[data-player-field=\"'+n+'\"]').hidden}).join()"), "false,false,false,false")
        for i, name in enumerate(["Alice", "Bob", "Cara", "Dan"], 1):
            p.type_text(f"#name{i}", name)
        p.click("button[type=submit]")
        p.wait_for("document.querySelector('svg.board')")
        self.assertEqual(p.js("document.querySelector('svg.board').getAttribute('viewBox')"), f"0 0 {self.PR} {self.PR}")
        self.assertEqual(p.js("document.querySelectorAll('svg.board rect[fill=\"#111c30\"]').length"), 11 * 11)
        self.assertEqual(p.js("document.querySelectorAll('.player-card').length"), 4)
        self.assertEqual(self.walls_left(p), ["Walls: 6"] * 4)
        self.assertEqual(self.turn(p), "Alice's turn")
        self.shot(p, "pointrush-start.png")
        # walk in from the four edges, one square each per round; Alice (first to move) arrives first
        paths = [[(9, 5), (8, 5), (7, 5), (6, 5), (5, 5)], [(5, 1), (5, 2), (5, 3), (5, 4)], [(1, 5), (2, 5), (3, 5), (4, 5)], [(5, 9), (5, 8), (5, 7), (5, 6)]]
        order = ["Alice", "Bob", "Cara", "Dan"]
        self.pr_click(p, 8, 5)         # two squares from Alice's pawn: refused, still her turn
        self.assertEqual(self.moves(p), 0)
        for step in range(5):
            for who in range(4):
                if step >= len(paths[who]):
                    continue
                self.assertIn(order[who], self.turn(p))
                self.pr_click(p, *paths[who][step])
        self.assertIn("Alice wins", self.turn(p))
        self.assertEqual(self.moves(p), 17)
        self.assertIn("Reached the center in 5 turns.", p.js("document.querySelector('.result').textContent"))
        self.assertIn("Alice: moved to f6", p.js("document.querySelector('.move-log li:last-child').textContent"))
        self.shot(p, "pointrush-finish.png")
        self.no_errors(p)

    def test_pointrush_with_two_players_by_default(self):
        p = self.page()
        p.goto(self.base + "/variants/pointrush/")
        p.click("button[type=submit]")
        p.wait_for("document.querySelector('svg.board')")
        self.assertEqual(self.walls_left(p), ["Walls: 12", "Walls: 12"])
        self.assertEqual(self.turn(p), "Player 1's turn")
        self.pr_click(p, 9, 5)
        self.assertEqual(self.turn(p), "Player 2's turn")
        self.pr_click(p, 1, 5)         # Player 2 started on the top edge
        self.assertEqual(self.turn(p), "Player 1's turn")
        self.assertEqual(self.moves(p), 2)
        self.no_errors(p)

    # ---- Custom Game (a variant: the players choose the board size, the walls, borrowed moves and the clock) ----
    def set_field(self, p, selector, value):
        p.js(f"(function(){{var e=document.querySelector({selector!r});e.value={value!r};e.dispatchEvent(new Event('input',{{bubbles:true}}));}})()")

    def test_custom_game_uses_the_chosen_board_walls_and_clock(self):
        p = self.page()
        p.goto(self.base + "/variants/custom/")
        self.shot(p, "custom-page.png")
        # the form starts out as classic Quoridor
        self.assertEqual(p.js("[document.querySelector('#size').value, document.querySelector('#walls').value, document.querySelector('#borrow').checked].join()"), "9,10,false")
        self.set_field(p, "#size", "5")
        self.set_field(p, "#walls", "2")
        self.set_field(p, "#clock", "60")
        p.js("document.querySelector('#borrow').click()")
        p.type_text("#name1", "Alice")
        p.type_text("#name2", "Bob")
        p.click("button[type=submit]")
        p.wait_for("document.querySelector('svg.board')")
        small = PAD * 2 + 5 * CELL + 4 * (PITCH - CELL)
        self.assertEqual(p.js("document.querySelector('svg.board').getAttribute('viewBox')"), f"0 0 {small} {small}")
        self.assertEqual(p.js("document.querySelectorAll('svg.board rect[fill=\"#111c30\"]').length"), 25)
        self.assertEqual(self.walls_left(p), ["Walls: 2", "Walls: 2"])
        self.assertEqual(self.turn(p), "Alice's turn")
        self.assertIn("60", p.js("document.querySelector('.turn-timer-text').textContent"))
        self.shot(p, "custom-start.png")
        self.no_errors(p)

    def test_custom_game_without_a_clock_and_with_a_bad_wall_count(self):
        p = self.page()
        p.goto(self.base + "/variants/custom/")
        self.set_field(p, "#walls", "31")
        p.click("button[type=submit]")
        self.assertFalse(p.js("document.querySelector('#walls-error').hidden"))
        self.assertEqual(p.js("document.querySelector('svg.board')"), None)
        self.set_field(p, "#walls", "0")      # typing again clears the message
        self.assertTrue(p.js("document.querySelector('#walls-error').hidden"))
        self.set_field(p, "#clock", "0")
        p.click("button[type=submit]")
        p.wait_for("document.querySelector('svg.board')")
        self.assertEqual(self.walls_left(p), ["Walls: 0", "Walls: 0"])
        self.assertTrue(p.js("document.querySelector('.turn-timer').hidden"))
        self.assertTrue(p.js("Array.from(document.querySelectorAll('.wall-chip')).every(function(b){return b.disabled})"))  # no walls: only pawn moves
        self.assertEqual(self.clocks(p), ["", ""])        # no clock at all, so no bank either
        self.no_errors(p)

    def test_walls_use_the_colour_of_the_player_who_placed_them(self):
        p = self.page()
        self.start_local(p)
        self.pick_wall(p, "h")
        p.click_at(*self.wall_xy(p, "h", 6, 4))   # Alice (cyan pawn)
        self.pick_wall(p, "h")
        p.click_at(*self.wall_xy(p, "h", 2, 1))   # Bob (orange pawn)
        fills = p.js("Array.from(document.querySelectorAll('svg.board g')).filter(function(g){return g.children.length===2 && g.children[0].getAttribute('rx')==='6'}).map(function(g){return Array.from(g.children).map(function(r){return r.getAttribute('fill')})})[0]")
        self.assertEqual(fills, ["#42d9f5", "#ff9f43"])
        self.no_errors(p)

    def test_local_move_clock_is_32_seconds_and_each_player_has_five_minutes(self):
        p = self.page()
        self.start_local(p)
        self.assertRegex(p.js("document.querySelector('.turn-timer').textContent"), r"Alice: 3[12]s left")
        c = self.clocks(p)
        self.assertRegex(c[0], r"^(5:00|4:5\d)$")     # Alice's has started to run
        self.assertEqual(c[1], "5:00")                 # Bob's waits for his turn
        self.click_cell(p, 7, 4)
        p.wait_for("document.querySelector('.turn-bar').textContent === \"Bob's turn\"")
        c = self.clocks(p)
        self.assertRegex(c[0], r"^(5:00|4:5\d)$")     # Alice keeps what she used: it is not given back
        self.assertRegex(c[1], r"^(5:00|4:5\d)$")
        self.no_errors(p)

    def test_local_turn_timer_counts_down_and_plays_when_time_is_up(self):
        p = self.page()
        p.goto(self.base + "/variants/custom/")
        self.set_field(p, "#clock", "15")
        p.type_text("#name1", "Alice")
        p.type_text("#name2", "Bob")
        p.click("button[type=submit]")
        p.wait_for("document.querySelector('svg.board')")
        self.assertRegex(p.js("document.querySelector('.turn-timer').textContent"), r"Alice: 1[45]s left")
        self.assertEqual(self.moves(p), 0)
        p.wait_for("document.querySelectorAll('.move-log li').length === 1", timeout=20)
        self.assertEqual(self.turn(p), "Bob's turn")
        self.assertIn("Time ran out. Alice moved to e2.", self.hint(p))
        self.assertRegex(p.js("document.querySelector('.turn-timer').textContent"), r"Bob: 1[45]s left")
        self.no_errors(p)

    def test_a_player_whose_five_minutes_run_out_loses(self):
        p = self.page()
        self.start_local(p)
        # a second, short game on the same page: 1 s per move and 2 s in the bank
        p.js("(function(){var d=document.createElement('div');d.id='quick';document.body.appendChild(d);"
             "QuoridorGame.mount(d,{mode:'local',turnSeconds:1,bankSeconds:2,names:['Al','Bo']});})()")
        p.wait_for("document.querySelector('#quick .result h2').textContent", timeout=12)
        self.assertEqual(p.js("document.querySelector('#quick .result h2').textContent"), "Bo wins")
        self.assertEqual(p.js("document.querySelector('#quick .result p').textContent"), "Al ran out of time.")
        self.no_errors(p)

    # ---- dragging a wall from the tray ----------------------------------------------------
    def anchor_xy(self, p, r, c):
        return self.board_xy(p, PAD + c * PITCH + CELL + 7, PAD + r * PITCH + CELL + 7)

    def test_a_wall_dragged_from_the_tray_is_placed_where_it_is_dropped(self):
        p = self.page()
        self.start_local(p)
        self.assertEqual(p.js("document.querySelector('.wall-tray-count').textContent"), "10")
        x, y = self.chip_xy(p, "v")
        ax, ay = self.anchor_xy(p, 6, 4)
        p.drag(x, y, ax, ay, release=False)
        self.assertTrue(p.js("document.querySelector('.game').classList.contains('is-carrying')"))
        self.assertEqual(self.moves(p), 0)                       # nothing is placed until it is let go
        self.shot(p, "drag-preview.png")
        p.send("Input.dispatchMouseEvent", type="mouseReleased", x=ax, y=ay, button="left", clickCount=1)
        p.pump(0.2)
        self.assertEqual(self.moves(p), 1)
        self.assertIn("placed wall e2v", p.js("document.querySelector('.move-log li').textContent"))
        self.assertEqual(self.walls_left(p), ["Walls: 9", "Walls: 10"])
        self.assertEqual(self.turn(p), "Bob's turn")
        self.assertEqual(p.js("document.querySelector('.wall-tray-count').textContent"), "10")   # Bob's tray now
        self.assertFalse(p.js("document.querySelector('.game').classList.contains('is-carrying')"))
        self.assertIsNone(p.js("document.querySelector('.wall-ghost')"))
        self.no_errors(p)

    def test_a_wall_dropped_on_a_forbidden_groove_or_off_the_board_is_not_placed(self):
        p = self.page()
        self.start_local(p)
        x, y = self.chip_xy(p, "h")
        p.drag(x, y, *self.anchor_xy(p, 6, 4))                   # a legal wall first
        self.assertEqual(self.moves(p), 1)
        x, y = self.chip_xy(p, "h")
        p.drag(x, y, *self.anchor_xy(p, 6, 4))                   # the same place again: overlaps
        self.assertEqual(self.moves(p), 1)
        self.assertIn("overlaps", self.hint(p))
        p.drag(x, y, x, y - 80)                                  # dropped between the board and the tray: off the board
        self.assertEqual(self.moves(p), 1)
        self.assertEqual(self.turn(p), "Bob's turn")
        self.no_errors(p)

    def test_phone_wall_drag_is_lifted_above_the_finger(self):
        p = self.page(width=390, height=844, mobile=True, touch=True)
        self.start_local(p)
        self.assertFalse(p.js("document.documentElement.scrollWidth > document.documentElement.clientWidth"))
        self.shot(p, "phone-game.png")
        # the board, both player cards and the tray are on screen together
        self.assertTrue(p.js("(function(){var r=document.querySelector('.wall-tray').getBoundingClientRect();return r.bottom <= innerHeight && document.querySelector('.players').getBoundingClientRect().top >= 0})()"))
        x, y = self.chip_xy(p, "h")
        ax, ay = self.anchor_xy(p, 6, 4)
        p.drag(x, y, ax, ay + 56)                                # the finger is 56 px below where the wall lands
        self.assertEqual(self.moves(p), 1)
        self.assertIn("placed wall e2h", p.js("document.querySelector('.move-log li').textContent"))
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
        self.assertFalse(p.js("document.querySelector('.wall-row').hidden"))     # W switched to wall mode
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
        self.pick_wall(p, "h")
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
        self.pick_wall(waiter, "h")
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
        self.assertEqual([h.split("play/")[1] for h in alts], ["computer", "create-room"])
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


    # ---- languages ----------------------------------------------------------------------
    def test_translate_button_switches_the_page_and_remembers_the_choice(self):
        p = self.page()
        p.goto(self.static_base + "/")
        self.assertEqual(p.js("document.documentElement.lang"), "en")
        self.assertTrue(p.js("document.getElementById('lang-menu').hidden"))
        p.click("#lang-toggle")
        self.assertFalse(p.js("document.getElementById('lang-menu').hidden"))
        self.assertEqual(p.js("document.getElementById('lang-toggle').getAttribute('aria-expanded')"), "true")
        p.key("Escape")
        self.assertTrue(p.js("document.getElementById('lang-menu').hidden"))
        p.click("#lang-toggle")
        p.click("[data-lang=es]")
        p.wait_for("document.documentElement.lang === 'es' && document.querySelector('h1').textContent === 'Juega a Quoridor en línea'")
        self.assertTrue(p.js("document.getElementById('lang-menu').hidden"))                    # picking closes the menu
        self.assertEqual(p.js("document.querySelector('[data-lang-code]').textContent"), "ES")
        self.assertNotIn("Play the Quoridor", p.js("document.title"))
        # links and icons survive the swap, and links still point at the right pages
        self.assertTrue(p.js("!!document.querySelector('.hero .btn--primary svg')"))
        self.assertRegex(p.js("document.querySelector('.hero .btn--primary').getAttribute('href')"), r"play$")
        self.assertRegex(p.js("document.querySelector('.faq a[href*=\"play/computer\"]').getAttribute('href')"), r"^\./play/computer$")
        # the choice follows the visitor to other pages
        p.goto(self.static_base + "/play/computer/")
        p.wait_for("document.documentElement.lang === 'es' && document.querySelector('h1').textContent === 'Juega a Quoridor contra el ordenador'")
        self.assertFalse(p.js("document.documentElement.classList.contains('i18n-pending')"))
        # Arabic reads right to left
        p.click("#lang-toggle")
        p.click("[data-lang=ar]")
        p.wait_for("document.documentElement.lang === 'ar' && document.documentElement.dir === 'rtl'")
        self.assertEqual(p.js("getComputedStyle(document.body).direction"), "rtl")
        self.assertFalse(p.js("document.documentElement.scrollWidth > document.documentElement.clientWidth"))
        self.shot(p, "language-arabic.png")
        # and back to English: the original text and structure return
        p.click("#lang-toggle")
        p.click("[data-lang=en]")
        p.wait_for("document.documentElement.lang === 'en' && document.querySelector('h1').textContent === 'Play Quoridor against the computer'")
        self.assertEqual(p.js("document.documentElement.dir"), "ltr")
        self.assertEqual(p.js("document.querySelector('#lang-toggle').getAttribute('aria-label')"), "Change language")
        self.assertTrue(p.js("!!document.querySelector('.stage button[type=submit] svg')"))
        self.no_errors(p)

    def test_every_page_is_translated_in_every_language(self):
        p = self.page()
        for lang, h1 in (("fr", "Jouez à Quoridor en ligne"), ("de", "Quoridor online spielen"), ("ar", "العب كوريدور عبر الإنترنت")):
            p.goto(self.static_base + "/?lang=" + lang)
            p.wait_for(f"document.documentElement.lang === '{lang}' && document.querySelector('h1').textContent === {h1!r}")
        pages = ("/", "/play/", "/play/online/", "/play/computer/", "/play/local/", "/play/create-room/", "/play/join-room/",
                 "/how-to-play-quoridor/", "/quoridor-rules/", "/quoridor-strategy/", "/quoridor-board-game/", "/about/",
                 "/contact/", "/privacy-policy/", "/terms/", "/nope/")
        collect = "Array.from(document.querySelectorAll('main h1, main h2, main h3, main .btn, main li, main summary')).map(function(e){return e.textContent.trim()}).filter(Boolean)"
        english = {}
        for path in pages:
            p.goto(self.static_base + path + "?lang=en")
            english[path] = p.js(collect)
        for lang in ("es", "fr", "de", "ar"):
            for path in pages:
                p.goto(self.static_base + path + "?lang=" + lang)
                p.wait_for(f"document.documentElement.lang === '{lang}' && !document.documentElement.classList.contains('i18n-pending')")
                now = p.js(collect)
                self.assertEqual(len(now), len(english[path]), f"{lang} {path}: text blocks went missing")
                same = [e for e, t in zip(english[path], now) if e == t and len(e) > 25]   # short words may be alike in two languages
                self.assertEqual(same, [], f"{lang} {path}: still English")
        self.no_errors(p)

    def test_changing_language_in_the_middle_of_a_game(self):
        p = self.page()
        p.goto(self.base + "/play/computer/?lang=es")
        p.wait_for("document.documentElement.lang === 'es'")
        p.click("button[type=submit]")
        p.wait_for("document.querySelector('svg.board')")
        self.assertEqual(self.turn(p), "Tu turno")
        self.assertIn("Robot medio", p.js("document.querySelector('.players').textContent"))
        self.assertEqual(self.walls_left(p), ["Muros: 10", "Muros: 10"])
        self.click_cell(p, 7, 4)
        p.wait_for("document.querySelector('.turn-bar').textContent === 'Tu turno'", timeout=15)
        self.assertIn("se movió a", p.js("document.querySelector('.move-log li').textContent"))
        p.click("#lang-toggle")
        p.click("[data-lang=fr]")
        p.wait_for("document.querySelector('.turn-bar').textContent === 'À vous de jouer'")
        self.assertIn("Robot moyen", p.js("document.querySelector('.players').textContent"))
        self.assertEqual(self.walls_left(p), ["Murs : 10", "Murs : 10"])
        self.assertEqual(p.js("document.querySelector('.wall-chip').getAttribute('aria-label')"), "Mur horizontal")
        self.assertIn("Plateau de Quoridor", p.js("document.querySelector('svg.board').getAttribute('aria-label')"))
        self.assertEqual(self.moves(p), 2)                                                   # the game itself is untouched
        self.assertIn("déplacement en", p.js("document.querySelector('.move-log li').textContent"))
        # a refused wall explains itself in the current language
        self.pick_wall(p, "h")
        p.click_at(*self.wall_xy(p, "h", 6, 4))      # a legal wall is placed ...
        p.wait_for("document.querySelector('.turn-bar').textContent === 'À vous de jouer'", timeout=15)
        self.pick_wall(p, "h")
        p.click_at(*self.wall_xy(p, "h", 6, 4))      # ... and the same slot is refused
        self.assertIn("chevauche", self.hint(p))
        p.click("#lang-toggle")
        p.click("[data-lang=ar]")
        p.wait_for("document.querySelector('.turn-bar').textContent === 'دورك'")
        self.assertEqual(p.js("document.documentElement.dir"), "rtl")
        self.no_errors(p)

    def test_players_who_use_different_languages_meet_and_play(self):
        """Matchmaking does not care about language: an Arabic page and a Spanish page are paired, each sees the game
        in its own language, names in any alphabet are shown correctly, and every move reaches the other side."""
        a, b = self.page(), self.page()
        a.goto(self.base + "/play/online/?lang=ar")
        a.wait_for("document.documentElement.lang === 'ar'")
        b.goto(self.base + "/play/online/?lang=es")
        b.wait_for("document.documentElement.lang === 'es'")
        a.type_text("#username", "ليلى")                 # Layla, in Arabic letters
        b.type_text("#username", "José")
        a.click("button[type=submit]")
        a.wait_for("!document.querySelector('[data-searching]').hidden")
        self.assertIn("البحث", a.js("document.querySelector('[data-search-text]').textContent"))        # "search", in Arabic
        b.click("button[type=submit]")
        for p in (a, b):
            p.wait_for("document.querySelector('svg.board')", timeout=20)
        self.assertEqual(sorted(a.js("Array.from(document.querySelectorAll('.player-name')).map(function(e){return e.textContent})")),
                         sorted(["ليلى", "José"]))
        self.assertEqual(a.js("document.documentElement.lang"), "ar")
        self.assertEqual(b.js("document.documentElement.lang"), "es")
        # one of them is on move, and reads that in its own language
        if self.turn(a) == "دورك":
            mover, waiter, waiter_turn = a, b, "Tu turno"
            self.assertIn("Turno de", self.turn(b))
        else:
            mover, waiter, waiter_turn = b, a, "دورك"
            self.assertEqual(self.turn(b), "Tu turno")
            self.assertIn("دور", self.turn(a))
        self.click_cell(mover, 7, 4)
        waiter.wait_for("document.querySelectorAll('.move-log li').length === 1", timeout=10)
        waiter.wait_for(f"document.querySelector('.turn-bar').textContent === {waiter_turn!r}", timeout=10)
        # each side reads the move in its own words
        self.assertIn("انتقل إلى", a.js("document.querySelector('.move-log li').textContent"))
        self.assertIn("se movió a", b.js("document.querySelector('.move-log li').textContent"))
        self.assertEqual(self.moves(a), self.moves(b))
        # a resignation is read in both languages too
        mover.js("window.confirm = function () { return true; }")
        mover.click(".game-controls .btn:nth-child(1)")
        for p in (a, b):
            p.wait_for("document.querySelector('.result') && !document.querySelector('.result').hidden", timeout=10)
        self.assertRegex(a.js("document.querySelector('.result h2').textContent"), "[؀-ۿ]")
        self.assertIn("gan", b.js("document.querySelector('.result h2').textContent").lower())
        self.no_errors(a)
        self.no_errors(b)

    def test_private_room_between_two_languages_and_names_in_any_alphabet(self):
        host, guest = self.page(), self.page()
        host.goto(self.base + "/play/create-room/?lang=de")
        host.wait_for("document.documentElement.lang === 'de'")
        host.type_text("#username", "Мария")             # a Cyrillic name
        host.click("button[type=submit]")
        host.wait_for("location.pathname.indexOf('/room/') === 0 && document.getElementById('invite-code').textContent.length === 6")
        self.assertIn("Warten", host.js("document.querySelector('[data-state=waiting] h1').textContent"))   # German waiting screen
        code = host.js("document.getElementById('invite-code').textContent")
        guest.goto(self.base + "/play/join-room/?lang=fr")
        guest.wait_for("document.documentElement.lang === 'fr'")
        guest.type_text("#username", "李雷")               # a Chinese name
        guest.type_text("#code", code)
        guest.click("button[type=submit]")
        for p in (host, guest):
            p.wait_for("document.querySelector('svg.board')", timeout=15)
        self.assertEqual(sorted(host.js("Array.from(document.querySelectorAll('.player-name')).map(function(e){return e.textContent})")),
                         sorted(["Мария", "李雷"]))
        turns = (self.turn(host), self.turn(guest))
        self.assertTrue(turns[0] == "Du bist dran" or turns[1] == "À vous de jouer", turns)
        # a wrong code is explained in the language of the person who typed it
        late = self.page()
        late.goto(self.base + "/play/join-room/?lang=es")
        late.wait_for("document.documentElement.lang === 'es'")
        late.type_text("#username", "Zed")
        late.type_text("#code", "ZZZZZZ")
        late.click("button[type=submit]")
        late.wait_for("!document.querySelector('#code-error').hidden")
        self.assertIn("no corresponde", late.js("document.querySelector('#code-error').textContent"))
        self.no_errors(host)
        self.no_errors(guest)

    # ---- the name this device remembers, and the score between friends -------------------------
    def test_the_username_is_remembered_on_this_device(self):
        p = self.page()
        p.goto(self.base + "/play/create-room/")
        self.assertEqual(p.js("document.querySelector('#username').value"), "")
        p.type_text("#username", "x")                    # not a valid name: nothing is remembered
        p.click("button[type=submit]")
        self.assertFalse(p.js("document.querySelector('#username-error').hidden"))
        self.assertIsNone(p.js("localStorage.getItem('quoridor.username')"))
        p.js("document.querySelector('#username').value = ''")
        p.type_text("#username", "Hana")
        p.click("button[type=submit]")
        p.wait_for("location.pathname.indexOf('/room/') === 0")
        self.assertEqual(p.js("localStorage.getItem('quoridor.username')"), "Hana")
        # every form that asks for a name has it filled in, and the one-device pages offer it as the first player
        for path in ("/play/join-room/", "/play/online/", "/play/create-room/"):
            p.goto(self.base + path)
            self.assertEqual(p.js("document.querySelector('#username').value"), "Hana", path)
        for path in ("/play/local/", "/variants/custom/"):
            p.goto(self.base + path)
            self.assertEqual(p.js("document.querySelector('#name1').value"), "Hana", path)
            self.assertEqual(p.js("document.querySelector('#name2').value"), "", path)
        # a guest who follows an invitation link is asked for a name too, and it is remembered
        link = self.page()
        link.goto(self.base + "/play/create-room/")
        link.type_text("#username", "Hana")
        link.click("button[type=submit]")
        link.wait_for("location.pathname.indexOf('/room/') === 0 && document.getElementById('invite-link').textContent.length > 10")
        invite = link.js("document.getElementById('invite-link').textContent")
        guest = self.page()
        guest.goto(invite)
        guest.wait_for("!document.querySelector('[data-state=join]').hidden")
        self.assertEqual(guest.js("document.querySelector('#username').value"), "")
        guest.type_text("#username", "Gus")
        guest.click("[data-state=join] button[type=submit]")
        guest.wait_for("document.querySelector('svg.board')", timeout=15)
        self.assertEqual(guest.js("localStorage.getItem('quoridor.username')"), "Gus")
        self.no_errors(p)
        self.no_errors(guest)

    def score(self, p):
        return p.js("document.querySelector('.score-line').hidden ? '' : document.querySelector('.score-line').textContent")

    def test_private_room_keeps_a_score_between_friends(self):
        host, guest = self.page(), self.page()
        self.make_room(host, guest)                      # Hana hosts, Gus joins
        for p in (host, guest):
            self.assertEqual(self.score(p), "")          # no game finished yet: nothing to show

        def finish(loser, host_score, guest_score):
            loser.js("window.confirm = function () { return true; }")
            loser.click(".game-controls .btn:nth-child(1)")   # Resign
            for p, text in ((host, host_score), (guest, guest_score)):
                p.wait_for("document.querySelector('.result') && !document.querySelector('.result').hidden", timeout=10)
                p.wait_for(f"document.querySelector('.score-line').textContent === {text!r}", timeout=5)

        def rematch():
            for p in (host, guest):
                p.click(".result .btn--primary")
            for p in (host, guest):
                p.wait_for("document.querySelectorAll('.move-log li').length === 0 && document.querySelector('.result').hidden", timeout=10)

        finish(host, "Score: Hana 0 – 1 Gus", "Score: Gus 1 – 0 Hana")   # each sees their own name on the left
        self.shot(host, "room-score.png")
        rematch()                                        # the seats swap, so the pages build the board again
        self.assertEqual(self.score(host), "Score: Hana 0 – 1 Gus")   # and the score is there from the first move
        finish(guest, "Score: Hana 1 – 1 Gus", "Score: Gus 1 – 1 Hana")
        rematch()
        finish(host, "Score: Hana 1 – 2 Gus", "Score: Gus 2 – 1 Hana")
        # showing a finished game again (a reload) does not count it twice
        host.goto(host.js("location.href"))
        host.wait_for("document.querySelector('.result') && !document.querySelector('.result').hidden", timeout=10)
        self.assertEqual(self.score(host), "Score: Hana 1 – 2 Gus")
        stored = host.js("JSON.parse(localStorage.getItem('quoridor.scores')).pairs.map(function (p) { return p.names.join('+') + ':' + p.wins.join('-') })")
        self.assertEqual(len(stored), 1)
        self.assertIn(stored[0], ("Gus+Hana:2-1", "Hana+Gus:1-2"))
        self.no_errors(host)
        self.no_errors(guest)

    def test_leaving_a_game_in_progress_counts_for_the_one_who_stays(self):
        host, guest = self.page(), self.page()
        self.make_room(host, guest)
        host.js("window.confirm = function () { return true; }")
        host.click(".game-controls .btn:nth-child(2)")   # Leave game: a forfeit
        host.wait_for("!document.querySelector('[data-state=left]').hidden")
        guest.wait_for("document.querySelector('.result') && !document.querySelector('.result').hidden", timeout=10)
        guest.wait_for("document.querySelector('.score-line').textContent === 'Score: Gus 1 – 0 Hana'", timeout=5)
        # the one who left has the loss on their own device too
        wins = host.js("(function () { var p = JSON.parse(localStorage.getItem('quoridor.scores')).pairs[0], o = {}; o[p.names[0]] = p.wins[0]; o[p.names[1]] = p.wins[1]; return o })()")
        self.assertEqual(wins, {"Gus": 1, "Hana": 0})

    def test_local_friends_who_typed_both_names_keep_a_score(self):
        p = self.page()
        self.start_local(p)                              # Alice and Bob
        alice = [(7, 4), (6, 4), (5, 4), (4, 4), (3, 4), (2, 4), (1, 4), (0, 4)]
        shuffle = [(0, 3), (0, 2), (0, 1), (0, 0), (1, 0), (2, 0), (3, 0)]

        def player_one_wins():                           # the first player walks straight up while the second wanders
            for i, move in enumerate(alice):
                self.click_cell(p, *move)
                if i < len(shuffle):
                    self.click_cell(p, *shuffle[i])

        player_one_wins()
        self.assertEqual(self.turn(p), "Alice wins!")
        self.assertEqual(self.score(p), "Score: Alice 1 – 0 Bob")
        self.shot(p, "local-score.png")
        p.click(".result .btn--primary")                 # Play again: the names are still in the form
        p.click("button[type=submit]")
        p.wait_for("document.querySelector('svg.board')")
        self.assertEqual(self.score(p), "Score: Alice 1 – 0 Bob")     # shown from the start of the next game
        for i in range(8):                               # Alice paces along her edge; Bob walks down his column
            self.click_cell(p, 8, (3, 2, 1, 0, 1, 0, 1, 0)[i])
            self.click_cell(p, i + 1, 4)
        self.assertEqual(self.turn(p), "Bob wins!")
        self.assertEqual(self.score(p), "Score: Alice 1 – 1 Bob")
        # a game where a name was left empty is not a game between two friends: no score
        p.click(".result .btn--primary")
        p.js("document.querySelector('#name2').value = ''")
        p.click("button[type=submit]")
        p.wait_for("document.querySelector('svg.board')")
        player_one_wins()
        self.assertEqual(self.turn(p), "Alice wins!")
        self.assertEqual(self.score(p), "")
        # the tally is still there after the page is closed and opened again
        p.goto(self.base + "/play/local/")
        self.assertEqual(p.js("JSON.parse(localStorage.getItem('quoridor.scores')).pairs[0].wins.join()"), "1,1")
        self.no_errors(p)

    def test_games_against_strangers_keep_no_score(self):
        a, b = self.page(), self.page()
        a.goto(self.base + "/play/online/")
        a.type_text("#username", "Cy")
        a.click("button[type=submit]")
        a.wait_for("!document.querySelector('[data-searching]').hidden")
        b.goto(self.base + "/play/online/")
        b.type_text("#username", "Di")
        b.click("button[type=submit]")
        for p in (a, b):
            p.wait_for("document.querySelector('svg.board')", timeout=20)
        a.js("window.confirm = function () { return true; }")
        a.click(".game-controls .btn:nth-child(1)")      # Resign
        for p in (a, b):
            p.wait_for("document.querySelector('.result') && !document.querySelector('.result').hidden", timeout=10)
            self.assertEqual(self.score(p), "")
            self.assertIsNone(p.js("localStorage.getItem('quoridor.scores')"))
        self.assertEqual(a.js("localStorage.getItem('quoridor.username')"), "Cy")   # the name is still remembered
        self.no_errors(a)
        self.no_errors(b)


if __name__ == "__main__":
    unittest.main()
