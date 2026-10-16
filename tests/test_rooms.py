"""Tests for rooms, matchmaking and presence (no HTTP). Run: python -m unittest discover tests"""

import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import rooms  # noqa: E402
from server.rooms import ApiError, Hub  # noqa: E402


def code_of(fn, *a, **k):
    try:
        fn(*a, **k)
    except ApiError as e:
        return e.code
    return None


def step_toward_goal(room, seat):
    """A legal pawn move that makes progress, for scripting a quick game."""
    g = room.game
    goal = 0 if seat == 0 else 8
    best = min(g.pawn_moves(seat), key=lambda m: abs(m[0] - goal))
    return {"type": "move", "r": best[0], "c": best[1]}


class Setup(unittest.TestCase):
    def setUp(self):
        self.hub = Hub()

    def start_game(self):
        host = self.hub.create_room("1.1.1.1", "Alex")
        guest = self.hub.join_by_code("2.2.2.2", host["code"], "Sam")
        room = self.hub.rooms[host["roomId"]]
        return room, {host["seat"]: host, guest["seat"]: guest}


class RoomFlow(Setup):
    def test_create_gives_unguessable_id_and_short_code(self):
        r = self.hub.create_room("1.1.1.1", "Alex")
        self.assertGreaterEqual(len(r["roomId"]), 22)
        self.assertRegex(r["code"], r"^[A-HJ-NP-Z2-9]{6}$")
        self.assertIn(r["seat"], (0, 1))

    def test_username_validation(self):
        for bad in ("", "a", "x" * 21, "<script>", None, 5):
            self.assertEqual(code_of(self.hub.create_room, "1.1.1.1", bad), "bad-username", bad)
        self.assertEqual(self.hub.create_room("1.1.1.1", "  Alex  ")["seat"] in (0, 1), True)

    def test_join_by_code_and_by_link(self):
        host = self.hub.create_room("1.1.1.1", "Alex")
        self.assertEqual(self.hub.peek("2.2.2.2", host["roomId"])["status"], "open")
        guest = self.hub.join_by_id("2.2.2.2", host["roomId"], "Sam")
        self.assertEqual(guest["seat"], 1 - host["seat"])
        room = self.hub.rooms[host["roomId"]]
        self.assertEqual(room.status, "playing")
        self.assertEqual(code_of(self.hub.peek, "3.3.3.3", host["roomId"]), "full")
        self.assertEqual(code_of(self.hub.join_by_id, "3.3.3.3", host["roomId"], "Eve"), "full")

    def test_code_stops_working_once_the_room_is_full(self):
        host = self.hub.create_room("1.1.1.1", "Alex")
        self.hub.join_by_code("2.2.2.2", host["code"], "Sam")
        self.assertEqual(code_of(self.hub.join_by_code, "3.3.3.3", host["code"], "Eve"), "invalid")

    def test_wrong_or_malformed_codes_look_the_same(self):
        for bad in ("ZZZZZZ", "abc", "", None, "ABCDE!", "A" * 40):
            self.assertEqual(code_of(self.hub.join_by_code, "9.9.9.9", bad, "Sam"), "invalid", bad)

    def test_unknown_room_is_unavailable(self):
        self.assertEqual(code_of(self.hub.peek, "1.1.1.1", "doesnotexist12345678"), "unavailable")

    def test_code_guessing_is_rate_limited(self):
        results = [code_of(self.hub.join_by_code, "6.6.6.6", "ZZZZZZ", "Sam") for _ in range(15)]
        self.assertEqual(results[:12], ["invalid"] * 12)
        self.assertEqual(set(results[12:]), {"rate-limited"})
        # Another address is unaffected.
        self.assertEqual(code_of(self.hub.join_by_code, "7.7.7.7", "ZZZZZZ", "Sam"), "invalid")


class Playing(Setup):
    def test_only_the_player_to_move_may_move_and_the_server_validates(self):
        room, seats = self.start_game()
        first, second = seats[0], seats[1]
        self.assertEqual(code_of(self.hub.move, "x", room.id, second["token"], {"type": "move", "r": 1, "c": 4}), "not-your-turn")
        self.assertEqual(code_of(self.hub.move, "x", room.id, first["token"], {"type": "move", "r": 3, "c": 3}), "illegal-move")
        self.assertEqual(code_of(self.hub.move, "x", room.id, first["token"], {"type": "teleport"}), "bad-move")
        self.assertEqual(code_of(self.hub.move, "x", room.id, "nope", {"type": "move", "r": 7, "c": 4}), "forbidden")
        snap = self.hub.move("x", room.id, first["token"], {"type": "move", "r": 7, "c": 4})
        self.assertEqual(snap["game"]["pawns"][0], [7, 4])
        self.assertEqual(snap["game"]["turn"], 1)

    def test_tokens_do_not_cross_rooms(self):
        room, seats = self.start_game()
        other, _ = Setup.start_game(self)
        self.assertEqual(code_of(self.hub.move, "x", other.id, seats[0]["token"], {"type": "move", "r": 7, "c": 4}), "forbidden")

    def test_full_game_to_a_win(self):
        room, seats = self.start_game()
        for _ in range(40):
            if room.status != "playing":
                break
            turn = room.game.turn
            self.hub.move("x", room.id, seats[turn]["token"], step_toward_goal(room, turn))
        self.assertEqual(room.status, "finished")
        self.assertIsNone(room.reason)
        self.assertIsNotNone(room.game.winner)
        self.assertEqual(code_of(self.hub.move, "x", room.id, seats[room.game.turn]["token"], {"type": "move", "r": 0, "c": 0}), "not-playing")

    def test_resign_and_rematch_swaps_the_first_mover(self):
        room, seats = self.start_game()
        self.hub.resign(room.id, seats[0]["token"])
        self.assertEqual((room.status, room.reason, room.game.winner), ("finished", "resign", 1))
        names_before = [s.name for s in room.seats]
        self.hub.rematch(room.id, seats[0]["token"])
        self.assertEqual(room.status, "finished")
        snap = self.hub.rematch(room.id, seats[1]["token"])
        self.assertEqual(room.status, "playing")
        self.assertEqual([s.name for s in room.seats], names_before[::-1])
        self.assertEqual(room.game.moves, [])
        # seat 1 became seat 0: the second player's snapshot says they now move first
        self.assertEqual(snap["you"], 0)
        self.assertEqual(code_of(self.hub.rematch, room.id, seats[0]["token"]), "not-finished")

    def test_leaving_mid_game_is_a_forfeit(self):
        room, seats = self.start_game()
        self.hub.leave(room.id, seats[1]["token"])
        self.assertEqual((room.status, room.reason, room.game.winner), ("finished", "resign", 0))
        self.assertEqual(code_of(self.hub.wait_state, room.id, seats[1]["token"], None), "forbidden")
        self.assertEqual(code_of(self.hub.rematch, room.id, seats[0]["token"]), "opponent-left")
        self.hub.leave(room.id, seats[0]["token"])
        self.assertNotIn(room.id, self.hub.rooms)

    def test_host_cancelling_a_waiting_room_removes_it_and_its_code(self):
        host = self.hub.create_room("1.1.1.1", "Alex")
        self.hub.leave(host["roomId"], host["token"])
        self.assertEqual(code_of(self.hub.join_by_code, "2.2.2.2", host["code"], "Sam"), "invalid")
        self.assertEqual(code_of(self.hub.peek, "2.2.2.2", host["roomId"]), "unavailable")

    def test_snapshot_only_shows_the_code_to_the_waiting_host(self):
        host = self.hub.create_room("1.1.1.1", "Alex")
        snap = self.hub.wait_state(host["roomId"], host["token"], None)
        self.assertEqual(snap["code"], host["code"])
        guest = self.hub.join_by_id("2.2.2.2", host["roomId"], "Sam")
        for who in (host, guest):
            self.assertNotIn("code", self.hub.wait_state(host["roomId"], who["token"], None))


class LongPoll(Setup):
    def test_poll_returns_when_the_opponent_moves(self):
        room, seats = self.start_game()
        mover, waiter = seats[0], seats[1]
        v = self.hub.wait_state(room.id, waiter["token"], None)["version"]
        out = {}

        def poll():
            out["snap"] = self.hub.wait_state(room.id, waiter["token"], v, timeout=5)

        t = threading.Thread(target=poll)
        t.start()
        time.sleep(0.2)
        self.hub.move("x", room.id, mover["token"], {"type": "move", "r": 7, "c": 4})
        t.join(3)
        self.assertFalse(t.is_alive())
        self.assertGreater(out["snap"]["version"], v)
        self.assertEqual(out["snap"]["game"]["pawns"][mover["seat"]], [7, 4])

    def test_a_waiting_poll_survives_a_rematch_seat_swap(self):
        room, seats = self.start_game()
        self.hub.resign(room.id, seats[0]["token"])
        self.hub.rematch(room.id, seats[0]["token"])
        v = self.hub.wait_state(room.id, seats[1]["token"], None)["version"]
        out = {}
        t = threading.Thread(target=lambda: out.update(self.hub.wait_state(room.id, seats[1]["token"], v, timeout=5)))
        t.start()
        time.sleep(0.2)
        self.hub.rematch(room.id, seats[1]["token"])   # starts the new game and swaps the seats
        t.join(3)
        self.assertEqual(out["status"], "playing")
        self.assertEqual(out["you"], 0)                 # the second player now moves first

    def test_poll_times_out_with_the_same_version(self):
        room, seats = self.start_game()
        v = self.hub.wait_state(room.id, seats[0]["token"], None)["version"]
        t0 = time.time()
        snap = self.hub.wait_state(room.id, seats[0]["token"], v, timeout=0.3)
        self.assertGreaterEqual(time.time() - t0, 0.25)
        self.assertEqual(snap["version"], v)


class Presence(Setup):
    def setUp(self):
        super().setUp()
        self._saved = (rooms.PRESENCE, rooms.FORFEIT_GRACE)
        rooms.PRESENCE, rooms.FORFEIT_GRACE = 0.2, 0.5

    def tearDown(self):
        rooms.PRESENCE, rooms.FORFEIT_GRACE = self._saved

    def test_disconnect_then_forfeit(self):
        room, seats = self.start_game()
        stay, gone = seats[0], seats[1]
        time.sleep(0.3)
        self.hub.wait_state(room.id, stay["token"], None)  # touches stay's last_seen only
        self.hub.sweep()
        snap = self.hub.wait_state(room.id, stay["token"], None)
        self.assertFalse(snap["players"][gone["seat"]]["connected"])
        self.assertIsNotNone(snap["forfeitIn"])
        self.assertEqual(room.status, "playing")
        time.sleep(0.6)
        self.hub.wait_state(room.id, stay["token"], None)
        self.hub.sweep()
        self.assertEqual((room.status, room.reason, room.game.winner), ("finished", "disconnect", stay["seat"]))

    def test_coming_back_cancels_the_forfeit(self):
        room, seats = self.start_game()
        time.sleep(0.3)
        for s in seats.values():
            self.hub.wait_state(room.id, s["token"], None)
        self.hub.sweep()
        time.sleep(0.1)
        for s in seats.values():
            self.hub.wait_state(room.id, s["token"], None)
        self.hub.sweep()
        time.sleep(0.6)
        for s in seats.values():
            self.hub.wait_state(room.id, s["token"], None)
        self.hub.sweep()
        self.assertEqual(room.status, "playing")

    def test_unjoined_rooms_expire(self):
        saved = rooms.WAITING_TTL
        rooms.WAITING_TTL = 0.1
        try:
            host = self.hub.create_room("1.1.1.1", "Alex")
            time.sleep(0.2)
            self.hub.sweep()
            self.assertNotIn(host["roomId"], self.hub.rooms)
            self.assertEqual(code_of(self.hub.join_by_code, "2.2.2.2", host["code"], "Sam"), "invalid")
        finally:
            rooms.WAITING_TTL = saved


class Matchmaking(Setup):
    def test_two_searchers_are_paired_into_a_room(self):
        a = self.hub.queue_join("1.1.1.1", "Alex")
        out = self.hub.queue_wait(a["ticket"], timeout=0.1)
        self.assertEqual(out["status"], "searching")
        b = self.hub.queue_join("2.2.2.2", "Sam")
        ra, rb = self.hub.queue_wait(a["ticket"], timeout=1), self.hub.queue_wait(b["ticket"], timeout=1)
        self.assertEqual((ra["status"], rb["status"]), ("matched", "matched"))
        self.assertEqual(ra["roomId"], rb["roomId"])
        self.assertEqual({ra["seat"], rb["seat"]}, {0, 1})
        room = self.hub.rooms[ra["roomId"]]
        self.assertEqual(room.status, "playing")
        self.assertEqual(sorted(s.name for s in room.seats), ["Alex", "Sam"])
        self.assertEqual(code_of(self.hub.queue_wait, a["ticket"], 0.1), "unavailable")  # ticket is single-use

    def test_cancel_leaves_the_queue(self):
        a = self.hub.queue_join("1.1.1.1", "Alex")
        self.hub.queue_cancel(a["ticket"])
        b = self.hub.queue_join("2.2.2.2", "Sam")
        self.assertEqual(self.hub.queue_wait(b["ticket"], timeout=0.1)["status"], "searching")

    def test_blocked_waiting_poll_wakes_on_match(self):
        a = self.hub.queue_join("1.1.1.1", "Alex")
        out = {}
        t = threading.Thread(target=lambda: out.update(self.hub.queue_wait(a["ticket"], timeout=5)))
        t.start()
        time.sleep(0.2)
        self.hub.queue_join("2.2.2.2", "Sam")
        t.join(3)
        self.assertEqual(out.get("status"), "matched")

    def test_stale_tickets_are_not_matched(self):
        saved = rooms.QUEUE_STALE
        rooms.QUEUE_STALE = 0.1
        try:
            a = self.hub.queue_join("1.1.1.1", "Alex")
            time.sleep(0.2)
            b = self.hub.queue_join("2.2.2.2", "Sam")
            self.assertEqual(self.hub.queue_wait(b["ticket"], timeout=0.1)["status"], "searching")
            self.assertEqual(code_of(self.hub.queue_wait, a["ticket"], 0.1), "unavailable")
        finally:
            rooms.QUEUE_STALE = saved


if __name__ == "__main__":
    unittest.main()
