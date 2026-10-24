"""Knockout tournaments for online play. Pure logic: no HTTP in here (server/api.py exposes it).

A tournament starts every 8 hours, at 00:00, 08:00 and 16:00 UTC, in two sizes: 8 players (three rounds) and 16 players
(four rounds). Both sizes of the next start are open for sign-up at any time. At the start time a tournament that has all
its players begins; one that has not is cancelled (nobody is carried over: players sign up again for the next start).
The bracket is drawn by lot at the start. Every match is an ordinary classic game in a room of its own (server/rooms.py),
created for the two players by the server, and the winner goes on to the next round. A player who does not open the match
within TOURNAMENT_JOIN_GRACE seconds forfeits it, so a bracket always finishes. There is no rematch.

Privacy-relevant facts (keep the Privacy Policy in step with these):
  * stored per player while a tournament exists: the display name, a random entry token, the order of sign-up
  * everyone can see the names in a tournament (the sign-up list, the bracket and its results)
  * a tournament is deleted KEEP_AFTER_END seconds after it ended; nothing is written to disk
  * nothing is kept about IP addresses here (the usual one-minute rate limit in server/rooms.py applies)
"""

import random
import secrets
import time
import unicodedata

from .rooms import ApiError, LONG_POLL, PRESENCE, Seat, clean_username

SLOT_SECONDS = 8 * 3600         # a tournament starts every 8 hours, on the hour counted from midnight UTC
SIZES = (8, 16)
KEEP_AFTER_END = 24 * 3600      # a finished or cancelled tournament stays listed this long
JOIN_LIMIT = 6                  # sign-ups per address per minute


def name_key(name):
    """'Sara' and 'sara' are one name."""
    return unicodedata.normalize("NFC", name).casefold()


class Entry:
    def __init__(self, name, seq):
        self.name = name
        self.token = secrets.token_urlsafe(24)   # proves this browser is that player; never shown to anyone else
        self.seq = seq                           # order of sign-up: decides a match nobody came to


class Match:
    def __init__(self):
        self.a = self.b = None       # indexes into Tournament.players, once the two players are known
        self.winner = None
        self.by = None               # "played" | "walkover" (the other player never opened the game)
        self.state = "waiting"       # waiting (a player is not known yet) -> live -> done
        self.room = None
        self.seats = {}              # player index -> the Seat they play from


class Tournament:
    def __init__(self, tid, size, start):
        self.id = tid
        self.size = size
        self.start = start                       # seconds since the epoch
        self.rounds_count = size.bit_length() - 1   # 8 -> 3, 16 -> 4
        self.status = "open"                     # open | playing | finished | cancelled
        self.reason = None                       # why it was cancelled: "not-enough"
        self.players = []                        # [Entry]: in sign-up order, then in bracket order once it starts
        self.rounds = []                         # [[Match]]: round 0 first, the final last
        self.champion = None
        self.version = 1
        self.ended = None                        # when it finished or was cancelled

    def index_of(self, token):
        if isinstance(token, str):
            for i, e in enumerate(self.players):
                if secrets.compare_digest(e.token, token):
                    return i
        return None

    def knocked_out(self):
        out = set()
        for rnd in self.rounds:
            for m in rnd:
                if m.state == "done":
                    out.add(m.b if m.winner == m.a else m.a)
        return out

    def current_round(self):
        for r, rnd in enumerate(self.rounds):
            if any(m.state != "done" for m in rnd):
                return r
        return None


class Tournaments:
    """All tournaments. They share the Hub's lock and clock-driven sweeper (Hub.sweep calls sweep() here)."""

    def __init__(self, hub, clock=time.time):
        self.hub = hub
        self.clock = clock          # wall-clock seconds: the schedule is in real time, not in the server's uptime
        self.items = {}             # id -> Tournament
        self._seq = 0

    # ---- time -----------------------------------------------------------------------------
    def _tick(self, now):
        """Make sure the next start has its tournaments, and begin (or cancel) the ones whose time has come."""
        start = (int(now) // SLOT_SECONDS + 1) * SLOT_SECONDS
        for size in SIZES:
            tid = f"t{size}-{start}"
            if tid not in self.items:
                self.items[tid] = Tournament(tid, size, start)
        for t in list(self.items.values()):
            if t.status == "open" and now >= t.start:
                if len(t.players) == t.size:
                    self._begin(t)
                else:
                    t.status, t.reason, t.ended = "cancelled", "not-enough", now
                    self._bump(t)

    def _bump(self, t):
        t.version += 1
        self.hub.cond.notify_all()

    def _get(self, tid):
        t = self.items.get(tid) if isinstance(tid, str) else None
        if t is None:
            raise ApiError(404, "no-tournament", "This tournament isn't available.")
        return t

    # ---- sign-up ---------------------------------------------------------------------------
    def join(self, ip, tid, username):
        with self.hub.cond:
            self.hub.limit(ip, "tjoin", JOIN_LIMIT)
            name = clean_username(username)
            now = self.clock()
            self._tick(now)
            t = self._get(tid)
            if t.status != "open":
                raise ApiError(409, "tournament-closed", "Sign-up for this tournament has closed.")
            if len(t.players) >= t.size:
                raise ApiError(409, "tournament-full", "This tournament is full.")
            key = name_key(name)
            # One name per start time, so nobody sits in the 8-player and the 16-player tournament at once.
            for other in self.items.values():
                if other.start == t.start and other.status == "open" and any(name_key(e.name) == key for e in other.players):
                    raise ApiError(409, "name-taken", "That name is already signed up for this start. Choose another.")
            self._seq += 1
            entry = Entry(name, self._seq)
            t.players.append(entry)
            self._bump(t)
            return {"token": entry.token, "index": len(t.players) - 1}

    def leave(self, tid, token):
        with self.hub.cond:
            self._tick(self.clock())
            t = self._get(tid)
            idx = t.index_of(token)
            if idx is None:
                raise ApiError(403, "not-signed-up", "You are not signed up for this tournament.")
            if t.status != "open":
                raise ApiError(409, "tournament-closed", "Sign-up for this tournament has closed.")
            del t.players[idx]
            self._bump(t)
            return {"left": True}

    # ---- the bracket -----------------------------------------------------------------------
    def _begin(self, t):
        random.shuffle(t.players)
        t.status = "playing"
        t.rounds = [[Match() for _ in range(t.size >> (r + 1))] for r in range(t.rounds_count)]
        for i, m in enumerate(t.rounds[0]):
            m.a, m.b = 2 * i, 2 * i + 1
        for slot in range(len(t.rounds[0])):
            self._open_match(t, 0, slot)
        self._bump(t)

    def _open_match(self, t, r, slot):
        """Give a match its room: both players are seated at once, the game is on, and the clock is held until they arrive."""
        m = t.rounds[r][slot]
        if m.state != "waiting" or m.a is None or m.b is None:
            return
        hub = self.hub
        a, b = t.players[m.a], t.players[m.b]
        try:
            room = hub._new_room(a.name)
        except ApiError:
            return                       # the server is full of rooms: the match stays "waiting" and sweep() tries again
        mine = room.host
        room.seats[1 - mine] = Seat(b.name)
        room.tournament = {"id": t.id, "round": r, "slot": slot, "rounds": t.rounds_count}
        gone = time.monotonic() - PRESENCE - 1       # nobody is connected until they open the room
        for s in room.seats:
            s.arrived = False
            s.last_seen = gone
        hub._start(room)
        m.room = room
        m.seats = {m.a: room.seats[mine], m.b: room.seats[1 - mine]}
        m.state = "live"

    def finished(self, room):
        """A tournament game is over (called by Hub._finish): record who goes on."""
        info = room.tournament
        t = self.items.get(info["id"])
        if t is None or t.status != "playing":
            return
        m = t.rounds[info["round"]][info["slot"]]
        if m.state != "live" or m.room is not room:
            return
        winner = None
        if room.game.winner is not None:
            seat = room.seats[room.game.winner]
            winner = next((p for p, s in m.seats.items() if s is seat), None)
        if winner is None:
            # Neither player ever came: whoever signed up first goes on, so the bracket still finishes.
            winner, by = min((m.a, m.b), key=lambda p: t.players[p].seq), "walkover"
        else:
            loser = m.b if winner == m.a else m.a
            by = "played" if m.seats[loser].arrived else "walkover"
        self._decide(t, info["round"], info["slot"], winner, by)

    def _decide(self, t, r, slot, winner, by):
        m = t.rounds[r][slot]
        m.winner, m.by, m.state = winner, by, "done"
        if r == t.rounds_count - 1:
            t.champion, t.status, t.ended = winner, "finished", self.clock()
        else:
            nxt = t.rounds[r + 1][slot // 2]
            if slot % 2 == 0:
                nxt.a = winner
            else:
                nxt.b = winner
            self._open_match(t, r + 1, slot // 2)
        self._bump(t)

    # ---- what clients see ---------------------------------------------------------------------
    def _summary(self, t):
        out = {
            "id": t.id, "size": t.size, "start": t.start, "status": t.status, "players": len(t.players),
            "rounds": t.rounds_count, "round": t.current_round(), "reason": t.reason,
            "champion": t.players[t.champion].name if t.champion is not None else None,
        }
        if t.status == "open":
            out["names"] = [e.name for e in t.players]
        return out

    def listing(self, ip):
        with self.hub.cond:
            self.hub.limit(ip, "tview", 240)
            now = self.clock()
            self._tick(now)
            ordered = sorted(self.items.values(), key=lambda t: (t.start, t.size))
            return {"now": now, "slotSeconds": SLOT_SECONDS, "tournaments": [self._summary(t) for t in ordered]}

    def _view(self, t, token, now):
        out = self._summary(t)
        out.pop("names", None)
        knocked = t.knocked_out()
        out.update({
            "version": t.version, "now": now,
            "players": [{"name": e.name, "out": i in knocked} for i, e in enumerate(t.players)],
            "bracket": [[{"a": m.a, "b": m.b, "winner": m.winner, "state": m.state, "by": m.by} for m in rnd] for rnd in t.rounds],
            "you": None,
        })
        me = t.index_of(token)
        if me is not None:
            state = "champion" if t.champion == me else "out" if me in knocked else "cancelled" if t.status == "cancelled" else "in"
            match = None
            for r, rnd in enumerate(t.rounds):
                for slot, m in enumerate(rnd):
                    if m.state == "live" and me in (m.a, m.b):
                        other = m.b if me == m.a else m.a
                        seat = m.seats[me]
                        match = {"round": r, "slot": slot, "opponent": t.players[other].name,
                                 "roomId": m.room.id, "token": seat.token, "seat": m.room.seats.index(seat)}
            out["you"] = {"index": me, "name": t.players[me].name, "state": state, "match": match}
        return out

    def state(self, ip, tid, token, since, timeout=LONG_POLL):
        """One tournament in full. With `since` (the version last seen) it waits for news, up to `timeout` seconds."""
        deadline = time.monotonic() + timeout
        with self.hub.cond:
            self.hub.limit(ip, "tview", 240)
            self._tick(self.clock())
            self._get(tid)
            while True:
                t = self._get(tid)
                remaining = deadline - time.monotonic()
                if since is None or t.version != since or remaining <= 0:
                    return self._view(t, token, self.clock())
                self.hub.cond.wait(min(remaining, 5))
                self._tick(self.clock())

    # ---- housekeeping -----------------------------------------------------------------------
    def sweep(self):
        """Called by Hub.sweep about once a second: starts, cancellations, a match whose room has vanished, old tournaments."""
        with self.hub.cond:
            now = self.clock()
            self._tick(now)
            for t in list(self.items.values()):
                if t.status == "playing":
                    for r, rnd in enumerate(t.rounds):
                        for slot, m in enumerate(rnd):
                            if m.state == "waiting":
                                self._open_match(t, r, slot)          # (a room could not be made earlier: try again)
                            elif m.state == "live" and m.room.id not in self.hub.rooms:
                                # The room is gone without a result, which should not happen; do not let the bracket stall.
                                winner = min((m.a, m.b), key=lambda p: t.players[p].seq)
                                self._decide(t, r, slot, winner, "walkover")
                elif t.ended is not None and now - t.ended > KEEP_AFTER_END:
                    del self.items[t.id]
