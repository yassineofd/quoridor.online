"""Variants on the server: the rules of the Python engine, and private rooms for Wallrush, Pointrush and Custom games
(rooms for 2 to 4 players, game settings, leaving, rematches). The JavaScript engine is compared with this one in
tests/test_parity_variants.py. Run: python -m unittest tests.test_variants"""

import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import rooms  # noqa: E402
from server.engine import Game  # noqa: E402
from server.rooms import ApiError, Hub, room_settings  # noqa: E402


def mv(r, c):
    return {"type": "move", "r": r, "c": c}


def wall(o, r, c):
    return {"type": "wall", "o": o, "r": r, "c": c}


def code_of(fn, *a, **k):
    try:
        fn(*a, **k)
    except ApiError as e:
        return e.code
    return None


class VariantRules(unittest.TestCase):
    def test_classic_is_the_default_and_unchanged(self):
        g = Game()
        self.assertEqual((g.variant, g.n_players, g.rows, g.cols), ("classic", 2, 9, 9))
        self.assertEqual(g.pawns, [(8, 4), (0, 4)])
        self.assertEqual(g.to_dict()["variant"], "classic")
        self.assertNotIn("options", g.to_dict())

    def test_unknown_variants_and_player_counts_are_refused(self):
        for args in (("nope",), ("classic", 3), ("wallrush", 4), ("pointrush", 5), ("pointrush", 1), ("pointrush", True),
                     ("pointrush", 2.0), ("custom", 3), (["classic"],), (5,)):
            with self.assertRaises(ValueError, msg=args):
                Game(*args)

    def test_wallrush_starts_on_one_row_and_both_race_to_the_top(self):
        g = Game("wallrush")
        self.assertEqual((g.rows, g.cols, g.pawns, g.walls_left), (13, 9, [(8, 2), (8, 6)], [10, 10]))
        g.pawns = [(1, 2), (5, 6)]
        self.assertIsNone(g.apply(mv(0, 2)))
        self.assertEqual(g.winner, 0)

    def test_wallrush_borrows_the_neighbours_moves_only_when_adjacent(self):
        g = Game("wallrush")
        g.pawns = [(6, 4), (6, 5)]
        self.assertIn((7, 5), g.pawn_moves(0))      # the neighbour could step down from (6, 5): borrowed
        self.assertNotIn((7, 5), Game("custom", 2, {"borrow": False}).pawn_moves(0))
        g.pawns = [(6, 2), (6, 6)]
        self.assertEqual(sorted(g.pawn_moves(0)), [(5, 2), (6, 1), (6, 3), (7, 2)])
        g.pawns = [(6, 4), (6, 5)]
        g.v.add((5, 4))                              # a wall between them ends the borrowing
        self.assertNotIn((7, 5), g.pawn_moves(0))

    def test_pointrush_setups(self):
        expect = {2: ([(10, 5), (0, 5)], [12, 12]), 3: ([(10, 5), (5, 0), (0, 5)], [8, 8, 8]), 4: ([(10, 5), (5, 0), (0, 5), (5, 10)], [6] * 4)}
        for n, (pawns, walls) in expect.items():
            g = Game("pointrush", n)
            self.assertEqual((g.pawns, g.walls_left, g.n_players, g.goal_cell), (pawns, walls, n, (5, 5)))
        self.assertEqual(Game("pointrush").n_players, 2)

    def test_pointrush_turns_pass_in_order_and_the_centre_wins(self):
        g = Game("pointrush", 3)
        order = []
        for _ in range(7):
            order.append(g.turn)
            moves = g.pawn_moves()
            g.apply(mv(*min(moves, key=lambda sq: g.distance(g.turn, sq))))
        self.assertEqual(order, [0, 1, 2, 0, 1, 2, 0])
        g = Game("pointrush", 4)
        g.pawns[1] = (5, 4)
        g.turn = 1
        self.assertIsNone(g.apply(mv(5, 5)))
        self.assertEqual((g.winner, g.turn), (1, 1))
        self.assertEqual(g.apply(mv(5, 4)), "game-over")

    def test_a_pawn_is_jumped_but_never_landed_on(self):
        g = Game("pointrush", 4)
        g.pawns = [(6, 5), (5, 5), (0, 5), (5, 10)]
        self.assertIn((4, 5), g.pawn_moves(0))                   # jump over the pawn on the centre
        g.pawns[2] = (4, 5)                                     # a third pawn behind it: no jump, side-step instead
        self.assertNotIn((4, 5), g.pawn_moves(0))
        self.assertIn((5, 4), g.pawn_moves(0))
        self.assertIn((5, 6), g.pawn_moves(0))
        self.assertNotIn((5, 5), g.pawn_moves(0))

    def test_every_pawn_must_keep_a_route_to_the_centre(self):
        g = Game("pointrush", 3)
        # The left pawn stands in a pocket of two squares (a wall above, a wall to its right): a wall below
        # would shut it in for good, so it is refused, although the other pawns would still have a route.
        g.h = {(3, 0)}
        g.v = {(4, 0)}
        self.assertIsNone(g.wall_error("h", 7, 0))
        self.assertEqual(g.wall_error("h", 5, 0), "blocks-path")

    def test_resign_hands_the_win_to_the_next_player(self):
        g = Game("pointrush", 4)
        g.resign(3)
        self.assertEqual(g.winner, 0)
        g = Game("pointrush", 3)
        g.resign(1)
        self.assertEqual(g.winner, 2)

    def test_custom_games_use_the_chosen_setup(self):
        g = Game("custom", 2, {"size": 7, "walls": 4, "borrow": True})
        self.assertEqual((g.rows, g.cols, g.pawns, g.walls_left, g.borrow, g.goals), (7, 7, [(6, 3), (0, 3)], [4, 4], True, [0, 6]))
        self.assertEqual(g.to_dict()["options"], {"size": 7, "walls": 4, "borrow": True})
        self.assertEqual(Game("custom").to_dict()["options"], {"size": 9, "walls": 10, "borrow": False})
        self.assertIsNone(g.apply(wall("h", 5, 5)))             # the last slot of a 7 x 7 board
        self.assertEqual(Game("custom", 2, {"size": 5}).wall_error("h", 4, 0), "out-of-bounds")

    def test_custom_options_are_checked(self):
        for bad in ({"size": 6}, {"size": 15}, {"size": "9"}, {"size": True}, {"walls": 31}, {"walls": -1}, {"walls": 2.5}, {"walls": "3"}, [], "x"):
            with self.assertRaises(ValueError, msg=bad):
                Game("custom", 2, bad)
        self.assertEqual(Game("custom", 2, {"walls": 0}).walls_left, [0, 0])
        self.assertEqual(Game("custom", 2, {"walls": 30}).walls_left, [30, 30])

    def test_timeout_move_steps_along_the_shortest_route_or_none(self):
        g = Game("wallrush")
        self.assertEqual(g.timeout_move(), {"type": "move", "r": 7, "c": 2})
        g.pawns[0] = (0, 0)
        g.winner = None
        g.h, g.v = {(0, 0)}, {(0, 0)}
        self.assertEqual(g.pawn_moves(0), [])
        self.assertIsNone(g.timeout_move())


class VariantRooms(unittest.TestCase):
    def setUp(self):
        self.hub = Hub()

    def make(self, n=3, variant="pointrush", **extra):
        host = self.hub.create_room("1.1.1.1", "Ana", dict({"variant": variant, "players": n}, **extra))
        room = self.hub.rooms[host["roomId"]]
        seats = {host["seat"]: host}
        names = iter(["Ben", "Cleo", "Dev"])
        for i in range(n - 1):
            g = self.hub.join_by_code(f"2.2.2.{i}", host["code"], next(names))
            seats[g["seat"]] = g
        return room, seats

    # ---- settings -------------------------------------------------------------------
    def test_settings_are_checked(self):
        bad = [{"variant": "chess"}, {"variant": 5}, {"variant": "pointrush", "players": 5}, {"variant": "wallrush", "players": 3},
               {"variant": "classic", "players": 2.0}, {"variant": "classic", "options": {"size": 7}}, {"variant": "classic", "turnSeconds": 15},
               {"variant": "custom", "options": {"size": 6}}, {"variant": "custom", "options": {"borrow": "false"}},
               {"variant": "custom", "options": {"colour": "red"}}, {"variant": "custom", "options": "big"},
               {"variant": "custom", "turnSeconds": 45}, {"variant": "custom", "turnSeconds": True}, {"variant": "custom", "turnSeconds": "32"},
               {"variant": "custom", "players": 3}]
        for i, settings in enumerate(bad):   # (a different address each time: creating rooms is rate-limited)
            self.assertEqual(code_of(self.hub.create_room, f"1.1.1.{i}", "Ana", settings), "bad-settings", settings)
        self.assertEqual(len(self.hub.rooms), 0)

    def test_settings_default_to_the_classic_game(self):
        s = room_settings({})
        self.assertEqual((s["variant"], s["players"], s["options"], s["clock"]), ("classic", 2, None, None))
        self.assertEqual(room_settings(None)["variant"], "classic")

    def test_every_variant_can_open_a_room(self):
        for settings in ({"variant": "wallrush"}, {"variant": "pointrush", "players": 4}, {"variant": "pointrush"},
                         {"variant": "custom", "options": {"size": 13, "walls": 0, "borrow": True}, "turnSeconds": 0},
                         {"variant": "custom"}):
            host = self.hub.create_room("1.1.1.1", "Ana", settings)
            room = self.hub.rooms[host["roomId"]]
            self.assertEqual(room.game.variant, settings["variant"])
            self.assertEqual(len(room.seats), settings.get("players", 2))

    # ---- the lobby ------------------------------------------------------------------
    def test_a_room_for_three_waits_until_the_third_player_joins(self):
        host = self.hub.create_room("1.1.1.1", "Ana", {"variant": "pointrush", "players": 3})
        room = self.hub.rooms[host["roomId"]]
        info = self.hub.peek("9.9.9.9", host["roomId"])
        self.assertEqual((info["variant"], info["players"], info["joined"], info["host"]), ("pointrush", 3, 1, "Ana"))
        second = self.hub.join_by_id("2.2.2.2", host["roomId"], "Ben")
        self.assertEqual(room.status, "waiting")
        self.assertNotEqual(second["seat"], host["seat"])
        self.assertEqual(self.hub.peek("9.9.9.9", host["roomId"])["joined"], 2)
        snap = self.hub.wait_state(room.id, second["token"], None)
        self.assertEqual((snap["status"], snap["you"], [p["name"] for p in snap["players"]].count(None)), ("waiting", second["seat"], 1))
        self.assertNotIn("code", snap)                              # only the host sees the pairing code
        self.assertEqual(self.hub.wait_state(room.id, host["token"], None)["code"], host["code"])
        third = self.hub.join_by_code("3.3.3.3", host["code"], "Cleo")   # the code still works: the room is not full yet
        self.assertEqual(room.status, "playing")
        self.assertEqual(sorted([host["seat"], second["seat"], third["seat"]]), [0, 1, 2])
        self.assertEqual(code_of(self.hub.join_by_code, "4.4.4.4", host["code"], "Dev"), "invalid")
        self.assertEqual(code_of(self.hub.join_by_id, "4.4.4.4", host["roomId"], "Dev"), "full")
        self.assertEqual(code_of(self.hub.peek, "4.4.4.4", host["roomId"]), "full")

    def test_a_waiting_player_is_told_when_someone_joins(self):
        host = self.hub.create_room("1.1.1.1", "Ana", {"variant": "pointrush", "players": 4})
        v = self.hub.wait_state(host["roomId"], host["token"], None)["version"]
        self.hub.join_by_id("2.2.2.2", host["roomId"], "Ben")
        snap = self.hub.wait_state(host["roomId"], host["token"], v, timeout=0.5)
        self.assertGreater(snap["version"], v)
        self.assertEqual(sum(p["name"] is not None for p in snap["players"]), 2)

    def test_a_guest_can_step_out_of_the_lobby_and_the_host_cancels_the_room(self):
        host = self.hub.create_room("1.1.1.1", "Ana", {"variant": "pointrush", "players": 3})
        room = self.hub.rooms[host["roomId"]]
        guest = self.hub.join_by_id("2.2.2.2", host["roomId"], "Ben")
        self.assertEqual(self.hub.leave(room.id, guest["token"]), {"left": True})
        self.assertIn(room.id, self.hub.rooms)
        self.assertEqual(sum(s is not None for s in room.seats), 1)
        self.assertEqual(code_of(self.hub.wait_state, room.id, guest["token"], None), "forbidden")
        again = self.hub.join_by_id("2.2.2.2", host["roomId"], "Ben")      # the seat is free again
        self.assertNotEqual(again["seat"], host["seat"])
        self.assertEqual(sum(s is not None for s in room.seats), 2)
        self.hub.leave(room.id, host["token"])
        self.assertNotIn(room.id, self.hub.rooms)

    def test_a_guest_who_vanishes_from_the_lobby_gives_their_seat_back(self):
        saved = rooms.FORFEIT_GRACE
        rooms.FORFEIT_GRACE = 0.1
        try:
            host = self.hub.create_room("1.1.1.1", "Ana", {"variant": "pointrush", "players": 3})
            room = self.hub.rooms[host["roomId"]]
            self.hub.join_by_id("2.2.2.2", host["roomId"], "Ben")
            time.sleep(0.25)
            self.hub.sweep()
            self.assertEqual(sum(s is not None for s in room.seats), 1)   # Ben never polled: gone; the host stays
        finally:
            rooms.FORFEIT_GRACE = saved

    # ---- playing --------------------------------------------------------------------
    def test_three_players_take_turns_and_the_first_on_the_centre_wins(self):
        room, seats = self.make(3)
        self.assertEqual((room.game.variant, room.game.n_players), ("pointrush", 3))
        snap = self.hub.wait_state(room.id, seats[0]["token"], None)
        self.assertEqual((snap["game"]["variant"], snap["game"]["players"], len(snap["players"])), ("pointrush", 3, 3))
        self.assertEqual(snap["turnSeconds"], 32)
        order = []
        for _ in range(60):
            if room.status != "playing":
                break
            turn = room.game.turn
            order.append(turn)
            target = min(room.game.pawn_moves(turn), key=lambda sq: room.game.distance(turn, sq))
            self.assertEqual(code_of(self.hub.move, "x", room.id, seats[(turn + 1) % 3]["token"], mv(*target)), "not-your-turn")
            self.hub.move("x", room.id, seats[turn]["token"], mv(*target))
        self.assertEqual(order[:6], [0, 1, 2, 0, 1, 2])
        self.assertEqual((room.status, room.reason), ("finished", None))
        self.assertEqual(room.game.winner, 0)      # the first player reaches the centre first when everybody simply walks

    def test_a_player_who_leaves_a_game_of_three_ends_it_with_no_winner(self):
        room, seats = self.make(3)
        self.hub.leave(room.id, seats[1]["token"])
        self.assertEqual((room.status, room.reason, room.quitter, room.game.winner), ("finished", "left", 1, None))
        snap = self.hub.wait_state(room.id, seats[0]["token"], None)
        self.assertEqual((snap["reason"], snap["quitter"], snap["game"]["winner"]), ("left", 1, None))
        self.assertEqual(code_of(self.hub.rematch, room.id, seats[0]["token"]), "opponent-left")
        self.hub.leave(room.id, seats[0]["token"])
        self.hub.leave(room.id, seats[2]["token"])
        self.assertNotIn(room.id, self.hub.rooms)

    def test_resigning_is_for_two_player_games_only(self):
        room, seats = self.make(3)
        self.assertEqual(code_of(self.hub.resign, room.id, seats[0]["token"]), "not-allowed")
        self.assertEqual(room.status, "playing")
        room, seats = self.make(2, "pointrush")
        self.hub.resign(room.id, seats[0]["token"])
        self.assertEqual((room.reason, room.game.winner), ("resign", 1))

    def test_a_disconnected_player_ends_a_game_of_four_with_no_winner(self):
        saved = (rooms.PRESENCE, rooms.FORFEIT_GRACE)
        rooms.PRESENCE, rooms.FORFEIT_GRACE = 0.05, 0.2
        try:
            room, seats = self.make(4)
            keep = [seats[i] for i in (0, 2, 3)]
            deadline = time.time() + 3
            while room.status == "playing" and time.time() < deadline:
                for s in keep:                       # everyone but seat 1 keeps checking in
                    room.seats[s["seat"]].last_seen = time.monotonic()
                self.hub.sweep()
                time.sleep(0.05)
            self.assertEqual((room.status, room.reason, room.quitter, room.game.winner), ("finished", "disconnect", 1, None))
        finally:
            rooms.PRESENCE, rooms.FORFEIT_GRACE = saved

    def test_the_forfeit_countdown_names_the_longest_absent_opponent(self):
        saved = (rooms.PRESENCE, rooms.FORFEIT_GRACE)
        rooms.PRESENCE, rooms.FORFEIT_GRACE = 0.05, 5
        try:
            room, seats = self.make(3)
            time.sleep(0.1)
            for i in (0, 2):
                room.seats[i].last_seen = time.monotonic()
            self.hub.sweep()
            snap = self.hub.wait_state(room.id, seats[0]["token"], None, timeout=0.01)
            self.assertFalse(snap["players"][1]["connected"])
            self.assertIsNotNone(snap["forfeitIn"])
            self.assertLessEqual(snap["forfeitIn"], 5)
        finally:
            rooms.PRESENCE, rooms.FORFEIT_GRACE = saved

    def test_running_out_of_time_in_a_game_of_three_hands_the_win_to_the_next_player(self):
        saved = (rooms.TURN_SECONDS, rooms.TURN_GRACE, rooms.BANK_SECONDS)
        rooms.BANK_SECONDS, rooms.TURN_GRACE = 0.1, 0
        try:
            room, seats = self.make(3)
            slow = room.game.turn
            time.sleep(0.25)
            self.hub.sweep()
            self.assertEqual((room.status, room.reason, room.game.winner), ("finished", "timeout", (slow + 1) % 3))
        finally:
            rooms.TURN_SECONDS, rooms.TURN_GRACE, rooms.BANK_SECONDS = saved

    def test_a_rematch_needs_everyone_and_the_next_player_moves_first(self):
        room, seats = self.make(3)
        before = [s.name for s in room.seats]
        room.game.winner = 0                    # pretend the game ended
        with self.hub.cond:
            self.hub._finish(room)
        self.hub.rematch(room.id, seats[0]["token"])
        self.hub.rematch(room.id, seats[1]["token"])
        self.assertEqual(room.status, "finished")
        snap = self.hub.rematch(room.id, seats[2]["token"])
        self.assertEqual(room.status, "playing")
        self.assertEqual([s.name for s in room.seats], before[1:] + before[:1])
        self.assertEqual(snap["round"], 2)
        self.assertEqual(snap["you"], 1)         # the last player to ask moved from seat 2 to seat 1

    # ---- the other variants ----------------------------------------------------------
    def test_a_wallrush_room_starts_on_the_tall_board(self):
        room, seats = self.make(2, "wallrush")
        snap = self.hub.wait_state(room.id, seats[0]["token"], None)
        self.assertEqual((snap["game"]["variant"], snap["game"]["pawns"]), ("wallrush", [[8, 2], [8, 6]]))
        self.hub.move("x", room.id, seats[0]["token"], mv(7, 2))
        self.assertEqual(code_of(self.hub.move, "x", room.id, seats[1]["token"], wall("h", 12, 0)), "out-of-bounds")

    def test_a_custom_room_keeps_its_setup_and_clock(self):
        room, seats = self.make(2, "custom", options={"size": 5, "walls": 2, "borrow": True}, turnSeconds=15)
        snap = self.hub.wait_state(room.id, seats[0]["token"], None)
        self.assertEqual(snap["game"]["options"], {"size": 5, "walls": 2, "borrow": True})
        self.assertEqual((snap["game"]["wallsLeft"], snap["turnSeconds"]), ([2, 2], 15))
        self.assertLessEqual(snap["turnLeft"], 15)
        info = self.hub.peek("1.2.3.4", self.hub.create_room("5.5.5.5", "Eve", {"variant": "custom", "options": {"size": 5}, "turnSeconds": 60})["roomId"])
        self.assertEqual((info["options"], info["turnSeconds"], info["variant"]), ({"size": 5, "walls": 10, "borrow": False}, 60, "custom"))

    def test_a_custom_room_can_have_no_clock(self):
        room, seats = self.make(2, "custom", turnSeconds=0)
        snap = self.hub.wait_state(room.id, seats[0]["token"], None)
        self.assertEqual((snap["turnSeconds"], snap["turnLeft"], snap["clocks"]), (0, None, None))
        room.turn_started -= 10_000             # no clock: nothing ever runs out
        self.hub.sweep()
        self.assertEqual((room.status, len(room.game.moves)), ("playing", 0))
        self.hub.move("x", room.id, seats[room.game.turn]["token"], mv(*min(room.game.pawn_moves(), key=lambda sq: sq[0])))

    def test_a_custom_clock_of_fifteen_seconds_is_enforced(self):
        saved = rooms.TURN_GRACE
        rooms.TURN_GRACE = 0
        try:
            room, seats = self.make(2, "custom", options={"size": 9, "walls": 10, "borrow": False}, turnSeconds=15)
            room.turn_started -= 16
            self.hub.sweep()
            self.assertEqual(len(room.game.moves), 1)      # the server played a pawn step for the slow player
        finally:
            rooms.TURN_GRACE = saved

    def test_the_standard_clock_is_not_used_for_a_custom_room(self):
        saved = rooms.TURN_GRACE
        rooms.TURN_GRACE = 0
        try:
            room, seats = self.make(2, "custom", turnSeconds=120)
            room.turn_started -= 60                        # past the standard 32 s, inside this room's 120 s
            self.hub.sweep()
            self.assertEqual(len(room.game.moves), 0)
        finally:
            rooms.TURN_GRACE = saved


if __name__ == "__main__":
    unittest.main()
