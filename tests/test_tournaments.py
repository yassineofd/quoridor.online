"""Tests for tournaments (no HTTP, no browser). Run: python -m unittest tests.test_tournaments

The tournaments follow the wall clock, so the tests give them a clock of their own and move it by hand.
"""

import datetime
import sys
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server import rooms  # noqa: E402
from server.rooms import ApiError, Hub  # noqa: E402
from server.tournaments import KEEP_AFTER_END, SLOT_SECONDS  # noqa: E402

BASE = 20_000 * SLOT_SECONDS          # a start time (a multiple of 8 hours)
LATER = BASE + SLOT_SECONDS


def code_of(fn, *a, **k):
    try:
        fn(*a, **k)
    except ApiError as e:
        return e.code
    return None


class Setup(unittest.TestCase):
    def setUp(self):
        self.hub = Hub()
        self.t = self.hub.tournaments
        self.now = BASE + 100.0       # a little into the slot whose tournaments start at LATER
        self.t.clock = lambda: self.now
        self.n = 0

    def find(self, size, start=LATER):
        return next(x for x in self.t.listing("9.9.9.9")["tournaments"] if x["size"] == size and x["start"] == start)

    def sign_up(self, size, count, prefix="Player", start=LATER):
        """`count` players sign up; returns [(name, token)]."""
        tid = self.find(size, start)["id"]
        out = []
        for i in range(count):
            self.n += 1
            name = f"{prefix} {self.n}"
            out.append((name, self.t.join(f"10.0.{self.n // 200}.{self.n % 200}", tid, name)["token"]))
        return tid, out

    def start(self, tid):
        self.now = LATER + 1.0
        return self.t.state("9.9.9.9", tid, None, None)

    def view(self, tid, token):
        return self.t.state("9.9.9.9", tid, token, None)

    def live_matches(self, tid):
        t = self.t.items[tid]
        return [(r, s, m) for r, rnd in enumerate(t.rounds) for s, m in enumerate(rnd) if m.state == "live"]

    def finish_round(self, tid, loser_of=lambda m: m.b):
        """Every live match is decided by the resignation of one player."""
        for r, s, m in self.live_matches(tid):
            p = loser_of(m)
            self.hub.resign(m.room.id, m.seats[p].token)


class Schedule(Setup):
    def test_a_tournament_of_each_size_is_open_for_the_next_start(self):
        listing = self.t.listing("9.9.9.9")
        self.assertEqual(listing["slotSeconds"], 8 * 3600)
        sizes = sorted((x["size"], x["start"], x["status"]) for x in listing["tournaments"])
        self.assertEqual(sizes, [(8, LATER, "open"), (16, LATER, "open")])

    def test_starts_are_at_midnight_8_and_16_utc(self):
        hours = set()
        for step in range(6):
            self.now = BASE + 100.0 + step * SLOT_SECONDS
            self.t.sweep()
        for x in self.t.listing("9.9.9.9")["tournaments"]:
            hours.add(datetime.datetime.fromtimestamp(x["start"], datetime.timezone.utc).hour)
        self.assertLessEqual(hours, {0, 8, 16})
        self.assertGreaterEqual(len(hours), 1)

    def test_the_next_start_is_always_ahead_never_now(self):
        self.now = LATER                        # exactly the start time
        starts = {x["start"] for x in self.t.listing("9.9.9.9")["tournaments"] if x["status"] == "open"}
        self.assertEqual(starts, {LATER + SLOT_SECONDS})

    def test_ids_are_stable_and_unguessable_parts_are_not_needed(self):
        a = self.find(8)["id"]
        self.assertEqual(self.find(8)["id"], a)
        self.assertRegex(a, r"^t8-\d+$")


class SigningUp(Setup):
    def test_signing_up_gives_an_entry_token_and_shows_the_name(self):
        tid, players = self.sign_up(8, 1)
        self.assertGreaterEqual(len(players[0][1]), 20)
        summary = self.find(8)
        self.assertEqual((summary["players"], summary["names"]), (1, [players[0][0]]))
        you = self.view(tid, players[0][1])["you"]
        self.assertEqual((you["name"], you["state"], you["match"]), (players[0][0], "in", None))
        self.assertIsNone(self.view(tid, "someone-else")["you"])
        self.assertIsNone(self.view(tid, None)["you"])

    def test_the_name_rules_of_every_game_apply(self):
        tid = self.find(8)["id"]
        for bad in ("", "a", "x" * 21, "<b>", None, 5):
            self.assertEqual(code_of(self.t.join, "1.1.1.1", tid, bad), "bad-username", bad)

    def test_one_name_per_start_even_in_the_other_size(self):
        tid8, _ = self.sign_up(8, 0)
        tid16 = self.find(16)["id"]
        self.t.join("1.1.1.1", tid8, "Sara")
        self.assertEqual(code_of(self.t.join, "2.2.2.2", tid8, "sara"), "name-taken")
        self.assertEqual(code_of(self.t.join, "2.2.2.2", tid16, " SARA "), "name-taken")
        self.assertIsNone(code_of(self.t.join, "2.2.2.2", tid16, "Sarah"))

    def test_a_full_tournament_takes_no_more_and_leaving_opens_a_place(self):
        tid, players = self.sign_up(8, 8)
        self.assertEqual(code_of(self.t.join, "5.5.5.5", tid, "Latecomer"), "tournament-full")
        self.assertEqual(self.t.leave(tid, players[3][1]), {"left": True})
        self.assertEqual(self.find(8)["players"], 7)
        self.assertIsNone(code_of(self.t.join, "5.5.5.5", tid, "Latecomer"))

    def test_leaving_needs_your_own_token(self):
        tid, players = self.sign_up(8, 2)
        self.assertEqual(code_of(self.t.leave, tid, "nope"), "not-signed-up")
        self.assertEqual(code_of(self.t.leave, tid, None), "not-signed-up")
        self.assertEqual(code_of(self.t.leave, "t8-1", players[0][1]), "no-tournament")

    def test_unknown_tournaments_are_not_available(self):
        self.assertEqual(code_of(self.t.join, "1.1.1.1", "t8-123", "Sara"), "no-tournament")
        self.assertEqual(code_of(self.t.state, "1.1.1.1", "nope", None, None), "no-tournament")

    def test_signing_up_is_rate_limited(self):
        tid = self.find(16)["id"]
        results = [code_of(self.t.join, "7.7.7.7", tid, f"Fast {i}") for i in range(8)]
        self.assertEqual(results[:6], [None] * 6)
        self.assertEqual(set(results[6:]), {"rate-limited"})

    def test_a_player_can_sign_up_again_after_withdrawing(self):
        tid, players = self.sign_up(8, 1)
        self.t.leave(tid, players[0][1])
        self.assertIsNone(code_of(self.t.join, "1.1.1.1", tid, players[0][0]))


class Starting(Setup):
    def test_not_enough_players_cancels_it_and_the_next_start_is_open(self):
        tid, players = self.sign_up(8, 7)
        self.now = LATER + 1
        view = self.t.state("9.9.9.9", tid, players[0][1], None)
        self.assertEqual((view["status"], view["reason"], view["you"]["state"]), ("cancelled", "not-enough", "cancelled"))
        self.assertEqual(code_of(self.t.join, "1.1.1.1", tid, "Late"), "tournament-closed")
        self.assertEqual(code_of(self.t.leave, tid, players[0][1]), "tournament-closed")
        nxt = [x for x in self.t.listing("9.9.9.9")["tournaments"] if x["status"] == "open"]
        self.assertEqual(sorted(x["size"] for x in nxt), [8, 16])
        self.assertEqual({x["start"] for x in nxt}, {LATER + SLOT_SECONDS})

    def test_nobody_signed_up_is_simply_cancelled(self):
        self.find(8)                # (the tournaments exist once anyone has looked, or the sweeper has run)
        self.now = LATER + 1
        self.t.sweep()
        self.assertEqual({x["status"] for x in self.t.listing("9.9.9.9")["tournaments"] if x["start"] == LATER}, {"cancelled"})

    def test_a_full_field_starts_at_the_start_time_and_not_before(self):
        tid, players = self.sign_up(8, 8)
        self.now = LATER - 1
        self.t.sweep()
        self.assertEqual(self.find(8)["status"], "open")
        self.now = LATER
        self.t.sweep()
        self.assertEqual(self.find(8)["status"], "playing")

    def test_the_eight_player_bracket_has_three_rounds(self):
        tid, players = self.sign_up(8, 8)
        view = self.start(tid)
        self.assertEqual(view["status"], "playing")
        self.assertEqual([len(r) for r in view["bracket"]], [4, 2, 1])
        self.assertEqual([m["state"] for m in view["bracket"][0]], ["live"] * 4)
        self.assertEqual([m["state"] for m in view["bracket"][1]], ["waiting"] * 2)
        self.assertEqual(sorted(p for m in view["bracket"][0] for p in (m["a"], m["b"])), list(range(8)))
        self.assertEqual(sorted(p["name"] for p in view["players"]), sorted(n for n, _ in players))

    def test_the_sixteen_player_bracket_has_four_rounds(self):
        tid, players = self.sign_up(16, 16)
        view = self.start(tid)
        self.assertEqual([len(r) for r in view["bracket"]], [8, 4, 2, 1])
        self.assertEqual(len(self.hub.rooms), 8)

    def test_the_draw_is_not_the_order_of_signing_up(self):
        orders = set()
        for _ in range(6):
            hub = Hub()
            hub.tournaments.clock = lambda: BASE + 100.0
            tid = next(x["id"] for x in hub.tournaments.listing("9.9.9.9")["tournaments"] if x["size"] == 8)
            for i in range(8):
                hub.tournaments.join(f"3.3.3.{i}", tid, f"Seed {i}")
            hub.tournaments.clock = lambda: LATER + 1
            view = hub.tournaments.state("9.9.9.9", tid, None, None)
            orders.add(tuple(p["name"] for p in view["players"]))
        self.assertGreater(len(orders), 1)


class Matches(Setup):
    def setUp(self):
        super().setUp()
        self.tid, self.players = self.sign_up(8, 8)
        self.start(self.tid)

    def test_each_player_is_told_their_match_and_holds_a_seat_in_it(self):
        mine = {}
        for name, token in self.players:
            you = self.view(self.tid, token)["you"]
            self.assertEqual(you["state"], "in")
            match = you["match"]
            self.assertEqual(match["round"], 0)
            self.assertNotEqual(match["opponent"], name)
            self.assertIn(match["seat"], (0, 1))
            mine[name] = match
        rooms_used = {m["roomId"] for m in mine.values()}
        self.assertEqual(len(rooms_used), 4)
        for name, token in self.players:                       # the seat token opens the room
            m = mine[name]
            snap = self.hub.wait_state(m["roomId"], m["token"], None, timeout=0)
            self.assertEqual((snap["status"], snap["you"], snap["tournament"]["round"], snap["tournament"]["rounds"]), ("playing", m["seat"], 0, 3))
            names = [p["name"] for p in snap["players"]]
            self.assertCountEqual(names, [name, m["opponent"]])

    def test_a_match_is_an_ordinary_classic_game(self):
        r, s, m = self.live_matches(self.tid)[0]
        snap = self.hub.wait_state(m.room.id, m.seats[m.a].token, None, timeout=0)
        self.assertEqual((snap["game"]["variant"], snap["game"]["players"], len(snap["players"])), ("classic", 2, 2))
        self.assertEqual(snap["turnSeconds"], rooms.TURN_SECONDS)

    def test_other_players_tokens_do_not_open_a_match(self):
        r, s, m = self.live_matches(self.tid)[0]
        other = self.live_matches(self.tid)[1][2]
        self.assertEqual(code_of(self.hub.wait_state, m.room.id, other.seats[other.a].token, None, 0), "forbidden")

    def test_the_clock_waits_for_players_to_arrive_and_the_opponent_sees_why(self):
        r, s, m = self.live_matches(self.tid)[0]
        a, b = m.seats[m.a], m.seats[m.b]
        self.assertEqual((a.arrived, b.arrived), (False, False))
        snap = self.hub.wait_state(m.room.id, a.token, None, timeout=0)
        self.assertTrue(a.arrived)
        other = snap["players"][1 - snap["you"]]
        self.assertEqual((other["arrived"], other["connected"]), (False, False))
        self.hub.sweep()
        snap = self.hub.wait_state(m.room.id, a.token, None, timeout=0)
        self.assertGreater(snap["forfeitIn"], rooms.FORFEIT_GRACE)           # a newcomer gets longer than a dropped connection
        self.assertLessEqual(snap["forfeitIn"], rooms.TOURNAMENT_JOIN_GRACE)

    def test_there_is_no_rematch_in_a_tournament(self):
        r, s, m = self.live_matches(self.tid)[0]
        self.hub.resign(m.room.id, m.seats[m.b].token)
        self.assertEqual(code_of(self.hub.rematch, m.room.id, m.seats[m.a].token), "tournament-match")

    def test_the_winner_goes_on_and_the_loser_is_out(self):
        r, s, m = self.live_matches(self.tid)[0]
        winner, loser = m.a, m.b
        wname = self.t.items[self.tid].players[winner].name
        snap = self.hub.resign(m.room.id, m.seats[loser].token)
        self.assertEqual((snap["status"], snap["reason"], snap["game"]["winner"]), ("finished", "resign", m.room.seats.index(m.seats[winner])))
        view = self.t.state("9.9.9.9", self.tid, None, None)
        done = view["bracket"][0][s]
        self.assertEqual((done["state"], done["winner"], done["by"]), ("done", winner, "played"))
        self.assertTrue(view["players"][loser]["out"])
        self.assertFalse(view["players"][winner]["out"])
        nxt = view["bracket"][1][s // 2]
        self.assertEqual(nxt["a" if s % 2 == 0 else "b"], winner)
        self.assertEqual(nxt["state"], "waiting")      # the other quarter-final is not over
        token = next(t for n, t in self.players if n == wname)
        self.assertEqual(self.view(self.tid, token)["you"]["match"], None)

    def test_the_next_match_opens_when_both_feeders_are_done(self):
        by_slot = {s: m for r, s, m in self.live_matches(self.tid)}
        for s in (0, 1):
            m = by_slot[s]
            self.hub.resign(m.room.id, m.seats[m.b].token)
        view = self.t.state("9.9.9.9", self.tid, None, None)
        self.assertEqual(view["bracket"][1][0]["state"], "live")
        self.assertEqual(view["bracket"][1][1]["state"], "waiting")
        winner = self.t.items[self.tid].players[by_slot[0].a]
        token = next(t for n, t in self.players if n == winner.name)
        match = self.view(self.tid, token)["you"]["match"]
        self.assertEqual((match["round"], match["slot"]), (1, 0))
        snap = self.hub.wait_state(match["roomId"], match["token"], None, timeout=0)
        self.assertEqual((snap["tournament"]["round"], snap["tournament"]["slot"]), (1, 0))

    def test_playing_it_through_to_a_champion(self):
        for _ in range(3):
            self.finish_round(self.tid)
        view = self.t.state("9.9.9.9", self.tid, None, None)
        self.assertEqual(view["status"], "finished")
        self.assertEqual([[m["state"] for m in r] for r in view["bracket"]], [["done"] * 4, ["done"] * 2, ["done"]])
        champ = view["bracket"][2][0]["winner"]
        self.assertEqual(view["champion"], view["players"][champ]["name"])
        self.assertEqual(sum(not p["out"] for p in view["players"]), 1)
        token = next(t for n, t in self.players if n == view["champion"])
        self.assertEqual(self.view(self.tid, token)["you"]["state"], "champion")
        loser_token = next(t for n, t in self.players if n != view["champion"])
        self.assertEqual(self.view(self.tid, loser_token)["you"]["state"], "out")
        self.assertEqual(self.find(8)["status"], "finished")
        self.assertEqual([x["champion"] for x in self.t.listing("9.9.9.9")["tournaments"] if x["id"] == self.tid], [view["champion"]])

    def test_a_game_won_by_reaching_the_goal_counts_too(self):
        r, s, m = self.live_matches(self.tid)[0]
        room = m.room
        for _ in range(60):
            if room.status != "playing":
                break
            seat = room.game.turn
            goal = 0 if seat == 0 else 8
            best = min(room.game.pawn_moves(seat), key=lambda mv: abs(mv[0] - goal))
            self.hub.move("x", room.id, next(sd.token for sd in room.seats if room.seats.index(sd) == seat), {"type": "move", "r": best[0], "c": best[1]})
        self.assertEqual(room.status, "finished")
        view = self.t.state("9.9.9.9", self.tid, None, None)
        self.assertEqual(view["bracket"][0][s]["state"], "done")
        self.assertEqual(view["bracket"][0][s]["by"], "played")


class NoShows(Setup):
    def setUp(self):
        super().setUp()
        self.tid, self.players = self.sign_up(8, 8)
        self.start(self.tid)
        self.r, self.s, self.m = self.live_matches(self.tid)[0]

    def expire(self, seat, by=200):
        seat.lost_at = time.monotonic() - by

    def test_a_player_who_never_comes_forfeits_after_the_longer_wait(self):
        a, b = self.m.seats[self.m.a], self.m.seats[self.m.b]
        self.hub.wait_state(self.m.room.id, a.token, None, timeout=0)    # a opens the match; b does not
        self.hub.sweep()
        self.expire(b, by=rooms.FORFEIT_GRACE + 5)                       # long enough for a dropped connection, not for a newcomer
        self.hub.sweep()
        self.assertEqual(self.m.state, "live")
        self.expire(b, by=rooms.TOURNAMENT_JOIN_GRACE + 5)
        self.hub.sweep()
        self.assertEqual((self.m.state, self.m.winner, self.m.by), ("done", self.m.a, "walkover"))
        self.assertEqual(self.m.room.reason, "disconnect")

    def test_nobody_comes_and_the_first_to_sign_up_goes_on(self):
        a, b = self.m.seats[self.m.a], self.m.seats[self.m.b]
        players = self.t.items[self.tid].players
        first = min((self.m.a, self.m.b), key=lambda p: players[p].seq)
        self.hub.sweep()
        for seat in (a, b):
            self.expire(seat)
        self.hub.sweep()
        self.assertEqual((self.m.state, self.m.winner, self.m.by), ("done", first, "walkover"))
        self.assertEqual(self.m.room.reason, "noshow")
        self.assertIsNone(self.m.room.game.winner)

    def test_a_dropped_connection_in_play_uses_the_usual_minute(self):
        a, b = self.m.seats[self.m.a], self.m.seats[self.m.b]
        for seat in (a, b):
            self.hub.wait_state(self.m.room.id, seat.token, None, timeout=0)
        self.expire(b, by=rooms.FORFEIT_GRACE + 5)
        b.last_seen = time.monotonic() - 100
        self.hub.sweep()
        self.assertEqual((self.m.state, self.m.winner, self.m.by), ("done", self.m.a, "played"))

    def test_leaving_a_match_loses_it(self):
        a, b = self.m.seats[self.m.a], self.m.seats[self.m.b]
        for seat in (a, b):
            self.hub.wait_state(self.m.room.id, seat.token, None, timeout=0)
        self.hub.leave(self.m.room.id, b.token)
        self.assertEqual((self.m.state, self.m.winner), ("done", self.m.a))
        a2 = self.hub.leave(self.m.room.id, a.token)           # (both leaving deletes the room; the result was kept)
        self.assertEqual(a2, {"left": True})
        self.assertEqual(self.t.items[self.tid].rounds[0][self.s].winner, self.m.a)

    def test_a_whole_bracket_of_no_shows_still_finds_a_champion(self):
        for _ in range(3):
            self.hub.sweep()
            for r, s, m in self.live_matches(self.tid):
                for seat in m.seats.values():
                    self.expire(seat)
            self.hub.sweep()
        view = self.t.state("9.9.9.9", self.tid, None, None)
        self.assertEqual(view["status"], "finished")
        players = self.t.items[self.tid].players
        self.assertEqual(view["champion"], min(players, key=lambda e: e.seq).name)   # the first to sign up wins every walkover

    def test_a_vanished_room_does_not_stall_the_bracket(self):
        with self.hub.cond:
            self.hub._delete(self.m.room)
        self.t.sweep()
        self.assertEqual((self.m.state, self.m.by), ("done", "walkover"))


class Housekeeping(Setup):
    def test_old_tournaments_are_forgotten(self):
        tid, _ = self.sign_up(8, 3)
        self.now = LATER + 1
        self.t.sweep()
        self.assertIn(tid, self.t.items)
        self.now = LATER + 1 + KEEP_AFTER_END + 1
        self.t.sweep()
        self.assertNotIn(tid, self.t.items)

    def test_the_hub_sweep_starts_tournaments(self):
        tid, _ = self.sign_up(8, 8)
        self.now = LATER + 2
        self.hub.sweep()
        self.assertEqual(self.t.items[tid].status, "playing")

    def test_waiting_for_news_returns_when_someone_signs_up(self):
        tid, _ = self.sign_up(8, 1)
        version = self.t.state("9.9.9.9", tid, None, None)["version"]
        out = {}

        def wait():
            out["view"] = self.t.state("9.9.9.9", tid, None, version, timeout=5)

        th = threading.Thread(target=wait)
        th.start()
        time.sleep(0.2)
        self.t.join("8.8.8.8", tid, "Newcomer")
        th.join(3)
        self.assertFalse(th.is_alive())
        self.assertEqual(out["view"]["players"][-1]["name"], "Newcomer")
        self.assertGreater(out["view"]["version"], version)

    def test_waiting_for_news_ends_at_the_timeout(self):
        tid, _ = self.sign_up(8, 1)
        version = self.t.state("9.9.9.9", tid, None, None)["version"]
        started = time.monotonic()
        view = self.t.state("9.9.9.9", tid, None, version, timeout=0.3)
        self.assertEqual(view["version"], version)
        self.assertGreaterEqual(time.monotonic() - started, 0.25)

    def test_an_empty_tournament_does_not_break_the_view(self):
        view = self.t.state("9.9.9.9", self.find(16)["id"], None, None)
        self.assertEqual((view["status"], view["players"], view["bracket"], view["champion"], view["round"]), ("open", [], [], None, None))

    def test_other_games_are_untouched_by_the_tournament_code(self):
        host = self.hub.create_room("1.1.1.1", "Alex")
        guest = self.hub.join_by_id("2.2.2.2", host["roomId"], "Sam")
        room = self.hub.rooms[host["roomId"]]
        self.assertIsNone(room.tournament)
        snap = self.hub.wait_state(room.id, guest["token"], None, timeout=0)
        self.assertIsNone(snap["tournament"])
        self.assertTrue(all(p["arrived"] for p in snap["players"]))
        self.hub.resign(room.id, host["token"])
        self.hub.rematch(room.id, host["token"])      # a friends' room can still ask for one
        self.hub.sweep()


if __name__ == "__main__":
    unittest.main()
