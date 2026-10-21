"""Rooms, matchmaking and presence for online play. Pure logic: no HTTP in here.

Everything lives in memory and is lost on restart; nothing is written to disk. The server is
authoritative: clients only ever send *intent* (a move) and receive the resulting state.

Privacy-relevant facts (keep docs/privacy-policy in step with these):
  * stored per player while a room exists: display name, a random seat token, last-seen time
  * rooms are deleted shortly after the game ends or the players leave (see the *_TTL values)
  * IP addresses are held in memory only, for rate limiting, and dropped after a minute
"""

import random
import re
import secrets
import threading
import time
import unicodedata
from collections import deque

from .engine import Game

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I
CODE_LENGTH = 6

# Timing (seconds)
PRESENCE = 15            # a seat counts as connected if it polled within this long (or is polling now)
FORFEIT_GRACE = 60       # a disconnected player forfeits after this long
WAITING_TTL = 30 * 60    # an unjoined room (and its code) expires
FINISHED_TTL = 10 * 60   # finished rooms are kept this long so players can ask for a rematch
ABANDONED_TTL = 5 * 60   # both players gone
QUEUE_STALE = 20         # a matchmaking ticket not polled for this long is dropped
OFFER_SECONDS = 20       # a player searching in the background has this long to accept a match
TURN_SECONDS = 32        # time to make a move; then the server plays one for the player
BANK_SECONDS = 300       # each player's time for the whole game (5 min); it only runs on their own turn
TURN_GRACE = 1.0         # extra time for a move that was sent just before the limit
LONG_POLL = 25           # max time a state request waits for news

MAX_ROOMS = 5000
MAX_QUEUE = 500


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def valid_username(name):
    """2 to 20 characters: letters and digits of any alphabet (with their accents and marks), spaces, dots,
    dashes and underscores. Language is no barrier here: a player can type their name in their own script.
    Control and direction-changing characters are not letters, so they are refused. (static/assets/js/play.js
    and room.js apply the same rule in the browser.)"""
    return 2 <= len(name) <= 20 and all(
        c.isalnum() or c in " _.-" or unicodedata.category(c).startswith("M") for c in name
    )


def clean_username(value):
    if not isinstance(value, str):
        raise ApiError(400, "bad-username", "Choose a name of 2 to 20 characters.")
    name = unicodedata.normalize("NFC", value.strip())
    if not valid_username(name):
        raise ApiError(400, "bad-username", "Use 2 to 20 characters: letters, numbers, spaces, dots, dashes or underscores.")
    return name


class Seat:
    def __init__(self, name):
        self.name = name
        self.token = secrets.token_urlsafe(24)
        self.last_seen = time.monotonic()
        self.polling = 0
        self.lost_at = None   # when the sweeper first saw this seat disconnected during a game
        self.left = False

    def connected(self, now):
        return not self.left and (self.polling > 0 or now - self.last_seen < PRESENCE)


class Room:
    def __init__(self, room_id, code, host_name):
        now = time.monotonic()
        self.id = room_id
        self.code = code
        self.created = now
        self.touched = now
        self.status = "waiting"           # waiting | playing | finished
        self.seats = [None, None]
        self.host = random.randrange(2)   # seat index the host will occupy
        self.seats[self.host] = Seat(host_name)
        self.game = Game()
        self.version = 1
        self.reason = None                # None (reached the edge) | resign | disconnect
        self.rematch = [False, False]
        self.presence = (True, True)
        self.finished_at = None
        self.turn_started = now           # when the player to move got the turn
        self.bank = [float(BANK_SECONDS)] * 2   # seconds left per seat, as of the start of the current turn


class Hub:
    def __init__(self):
        self.cond = threading.Condition()
        self.rooms = {}
        self.codes = {}
        self.tickets = {}  # ticket id -> dict(name, created, polled, result)
        self.hits = {}     # (ip, bucket) -> deque of timestamps
        self._sweeper = None

    # ---- rate limiting ------------------------------------------------------------------
    def limit(self, ip, bucket, count, per=60):
        now = time.monotonic()
        q = self.hits.setdefault((ip, bucket), deque())
        while q and now - q[0] > per:
            q.popleft()
        if len(q) >= count:
            raise ApiError(429, "rate-limited", "Too many attempts. Try again in a minute.")
        q.append(now)

    # ---- helpers ------------------------------------------------------------------------
    def _new_room(self, host_name):
        if len(self.rooms) >= MAX_ROOMS:
            raise ApiError(503, "busy", "The server is busy. Try again in a moment.")
        room_id = secrets.token_urlsafe(16)  # 128 bits
        while True:
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
            if code not in self.codes:
                break
        room = Room(room_id, code, host_name)
        self.rooms[room_id] = room
        self.codes[code] = room_id
        return room

    def _bump(self, room):
        room.version += 1
        room.touched = time.monotonic()
        self.cond.notify_all()

    def _start(self, room):
        room.status = "playing"
        room.game = Game()
        room.reason = None
        room.rematch = [False, False]
        room.finished_at = None
        room.turn_started = time.monotonic()
        room.bank = [float(BANK_SECONDS)] * 2
        for s in room.seats:
            s.lost_at = None
        self.codes.pop(room.code, None)
        self._bump(room)

    def _finish(self, room, reason=None):
        room.status = "finished"
        room.reason = reason
        room.finished_at = time.monotonic()
        room.rematch = [False, False]
        self._bump(room)

    def _charge(self, room, seat, now):
        """Take the time the player to move has used this turn off their bank."""
        room.bank[seat] = max(0.0, room.bank[seat] - (now - room.turn_started))

    def _seat_of(self, room, token):
        if isinstance(token, str):
            for i, s in enumerate(room.seats):
                if s is not None and not s.left and secrets.compare_digest(s.token, token):
                    return i
        raise ApiError(403, "forbidden", "You are not part of this room.")

    def _room(self, room_id):
        room = self.rooms.get(room_id)
        if room is None:
            raise ApiError(404, "unavailable", "This room isn't available.")
        return room

    def snapshot(self, room, seat_index):
        now = time.monotonic()
        other = room.seats[1 - seat_index]
        players = []
        for s in room.seats:
            players.append({"name": s.name if s else None, "connected": bool(s and s.connected(now))})
        forfeit_in = None
        if room.status == "playing" and other is not None and not other.connected(now) and other.lost_at is not None:
            forfeit_in = max(0.0, FORFEIT_GRACE - (now - other.lost_at))
        playing = room.status == "playing"
        elapsed = now - room.turn_started
        clocks = list(room.bank)
        turn_left = None
        if playing:
            clocks[room.game.turn] = max(0.0, clocks[room.game.turn] - elapsed)
            turn_left = max(0.0, min(TURN_SECONDS - elapsed, clocks[room.game.turn]))
        out = {
            "version": room.version,
            "status": room.status,
            "you": seat_index,
            "players": players,
            "game": room.game.to_dict(),
            "reason": room.reason,
            "rematch": list(room.rematch),
            "forfeitIn": forfeit_in,
            "turnLeft": turn_left,
            "clocks": clocks,
        }
        if room.status == "waiting" and seat_index == room.host:
            out["code"] = room.code
        return out

    # ---- private rooms ------------------------------------------------------------------
    def create_room(self, ip, username):
        with self.cond:
            self.limit(ip, "create", 10)
            name = clean_username(username)
            room = self._new_room(name)
            seat = room.seats[room.host]
            return {"roomId": room.id, "code": room.code, "token": seat.token, "seat": room.host}

    def peek(self, ip, room_id):
        """Can a stranger holding this link join? (They hold the unguessable id, so 'full' may be said.)"""
        with self.cond:
            self.limit(ip, "peek", 60)
            room = self.rooms.get(room_id)
            if room is None or room.status == "finished" and all(s is None or s.left for s in room.seats):
                raise ApiError(404, "unavailable", "This room isn't available.")
            if room.status != "waiting":
                raise ApiError(409, "full", "This room already has two players.")
            return {"status": "open", "host": room.seats[room.host].name}

    def _join(self, room, name):
        if room.status != "waiting":
            raise ApiError(409, "full", "This room already has two players.")
        idx = 1 - room.host
        room.seats[idx] = Seat(name)
        self._start(room)
        return {"roomId": room.id, "token": room.seats[idx].token, "seat": idx}

    def join_by_id(self, ip, room_id, username):
        with self.cond:
            self.limit(ip, "join", 12)
            name = clean_username(username)
            return self._join(self._room(room_id), name)

    def join_by_code(self, ip, code, username):
        with self.cond:
            self.limit(ip, "join", 12)
            name = clean_username(username)
            code = code.strip().upper() if isinstance(code, str) else ""
            room_id = self.codes.get(code) if re.fullmatch(r"[A-Z0-9]{%d}" % CODE_LENGTH, code) else None
            room = self.rooms.get(room_id) if room_id else None
            if room is None:
                raise ApiError(404, "invalid", "That code doesn't match a room. Check it and try again.")
            return self._join(room, name)

    # ---- state / long poll --------------------------------------------------------------
    def wait_state(self, room_id, token, since, timeout=LONG_POLL):
        deadline = time.monotonic() + timeout
        with self.cond:
            room = self._room(room_id)
            idx = self._seat_of(room, token)
            seat = room.seats[idx]
            seat.polling += 1
            try:
                while True:
                    room = self.rooms.get(room_id)
                    if room is None or seat.left or seat not in room.seats:
                        raise ApiError(404, "unavailable", "This room isn't available.")
                    idx = room.seats.index(seat)  # a rematch swaps the seats, so look it up each time
                    if since is None or room.version != since:
                        break
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    self.cond.wait(remaining)
                return self.snapshot(room, idx)
            finally:
                seat.polling -= 1
                seat.last_seen = time.monotonic()

    # ---- actions ------------------------------------------------------------------------
    def move(self, ip, room_id, token, move):
        with self.cond:
            self.limit(ip, "move", 240)
            room = self._room(room_id)
            idx = self._seat_of(room, token)
            room.seats[idx].last_seen = time.monotonic()
            if room.status != "playing":
                raise ApiError(409, "not-playing", "The game is not in progress.")
            if room.game.turn != idx:
                raise ApiError(409, "not-your-turn", "It is not your turn.")
            err = room.game.apply(move)
            if err:
                raise ApiError(422, err, "That move is not allowed.")
            now = time.monotonic()
            self._charge(room, idx, now)
            room.turn_started = now
            if room.game.winner is not None:
                self._finish(room)
            else:
                self._bump(room)
            return self.snapshot(room, idx)

    def resign(self, room_id, token):
        with self.cond:
            room = self._room(room_id)
            idx = self._seat_of(room, token)
            if room.status == "playing":
                room.game.resign(idx)
                self._finish(room, "resign")
            return self.snapshot(room, idx)

    def leave(self, room_id, token):
        with self.cond:
            room = self._room(room_id)
            idx = self._seat_of(room, token)
            if room.status == "playing":
                room.game.resign(idx)
                self._finish(room, "resign")
            if room.status == "waiting":
                self._delete(room)
                return {"left": True}
            room.seats[idx].left = True
            room.rematch = [False, False]
            self._bump(room)
            if all(s is None or s.left for s in room.seats):
                self._delete(room)
            return {"left": True}

    def rematch(self, room_id, token):
        with self.cond:
            room = self._room(room_id)
            idx = self._seat_of(room, token)
            if room.status != "finished":
                raise ApiError(409, "not-finished", "The game is not over yet.")
            other = room.seats[1 - idx]
            if other is None or other.left:
                raise ApiError(409, "opponent-left", "Your opponent has left the room.")
            room.rematch[idx] = True
            if all(room.rematch):
                room.seats.reverse()   # swap who moves first, so seat numbers change
                room.host = 1 - room.host
                idx = 1 - idx
                self._start(room)
            else:
                self._bump(room)
            return self.snapshot(room, idx)

    def _delete(self, room):
        self.rooms.pop(room.id, None)
        if self.codes.get(room.code) == room.id:
            self.codes.pop(room.code, None)
        self.cond.notify_all()

    # ---- matchmaking ----------------------------------------------------------------------
    def queue_join(self, ip, username):
        with self.cond:
            self.limit(ip, "queue", 15)
            name = clean_username(username)
            now = time.monotonic()
            self._drop_stale_tickets(now)
            if len(self.tickets) >= MAX_QUEUE:
                raise ApiError(503, "busy", "The server is busy. Try again in a moment.")
            ticket_id = secrets.token_urlsafe(18)
            # away: the player left the search page (e.g. to play the computer) and keeps searching in the
            # background. An away player is only matched after saying yes to an offer; v counts changes.
            self.tickets[ticket_id] = {
                "name": name, "created": now, "polled": now, "result": None, "seq": next(_seq),
                "away": False, "v": 1, "offer": None, "avoid": set(), "gen": 0,
            }
            self._pair(ticket_id)
            return {"ticket": ticket_id}

    def _ticket(self, ticket_id):
        t = self.tickets.get(ticket_id)
        if t is None:
            raise ApiError(404, "unavailable", "That search is no longer active.")
        return t

    def _pair(self, ticket_id):
        """Offer this ticket an opponent. Players on the search page come first: an away player has
        to be asked, so pairing someone with them makes the other side wait for the answer."""
        mine = self.tickets.get(ticket_id)
        if mine is None or mine["result"] is not None or mine["offer"] is not None:
            return
        others = [(t["away"], t["seq"], tid) for tid, t in self.tickets.items()
                  if tid != ticket_id and t["result"] is None and t["offer"] is None
                  and tid not in mine["avoid"] and ticket_id not in t["avoid"]]
        if not others:
            return
        _, _, other_id = min(others)
        a, b = mine, self.tickets[other_id]
        offer = {"id": next(_seq), "ids": (ticket_id, other_id), "deadline": time.monotonic() + OFFER_SECONDS,
                 "yes": {ticket_id: not a["away"], other_id: not b["away"]}}
        a["offer"] = b["offer"] = offer
        a["v"] += 1
        b["v"] += 1
        if all(offer["yes"].values()):
            self._complete(offer)
        self.cond.notify_all()

    def _complete(self, offer):
        """Everyone said yes: create the room. The player who searched longest hosts."""
        first_id, second_id = sorted(offer["ids"], key=lambda i: self.tickets[i]["seq"])
        first, second = self.tickets[first_id], self.tickets[second_id]
        room = self._new_room(first["name"])
        guest = Seat(second["name"])
        idx = 1 - room.host
        room.seats[idx] = guest
        self._start(room)
        first["result"] = {"roomId": room.id, "token": room.seats[room.host].token, "seat": room.host}
        second["result"] = {"roomId": room.id, "token": guest.token, "seat": idx}
        for t in (first, second):
            t["offer"] = None
            t["v"] += 1
        self.cond.notify_all()

    def _dissolve(self, offer, avoid=False, drop=()):
        """Take an offer apart. Tickets in `drop` leave the queue; the rest search again, and are not
        offered each other again if `avoid` (a decline)."""
        ids = offer["ids"]
        for tid in ids:
            t = self.tickets.get(tid)
            if t is not None:
                t["offer"] = None
                t["v"] += 1
                if avoid:
                    t["avoid"].update(i for i in ids if i != tid)
        for tid in drop:
            self.tickets.pop(tid, None)
        for tid in ids:
            if tid not in drop:
                self._pair(tid)
        self.cond.notify_all()

    def _drop_ticket(self, ticket_id):
        t = self.tickets.get(ticket_id)
        if t is None:
            return
        if t["offer"] is not None:
            self._dissolve(t["offer"], drop=(ticket_id,))
        else:
            self.tickets.pop(ticket_id, None)

    def _expire_offers(self, now):
        """An offer nobody answered in time ends the search of whoever stayed silent (so a player who
        walked away can't keep making others wait); the other side goes back to searching."""
        done = set()
        for t in list(self.tickets.values()):
            o = t["offer"]
            if o is not None and o["id"] not in done and now > o["deadline"]:
                done.add(o["id"])
                self._dissolve(o, drop=[tid for tid in o["ids"] if not o["yes"].get(tid)])

    def _drop_stale_tickets(self, now):
        self._expire_offers(now)
        for tid in [t for t, v in self.tickets.items() if (v["result"] is None and now - v["polled"] > QUEUE_STALE) or now - v["created"] > 600]:
            self._drop_ticket(tid)

    def _accept(self, ticket_id):
        t = self.tickets[ticket_id]
        offer = t["offer"]
        offer["yes"][ticket_id] = True
        if all(offer["yes"].values()):
            self._complete(offer)
        else:
            for tid in offer["ids"]:
                self.tickets[tid]["v"] += 1
            self.cond.notify_all()

    def _set_away(self, ticket_id, away):
        t = self.tickets[ticket_id]
        t["away"] = away
        offer = t["offer"]
        if offer is not None and not away and not offer["yes"].get(ticket_id):
            self._accept(ticket_id)  # back on the search page with an offer waiting: that means yes

    def _view(self, ticket_id, t, now):
        out = {"status": "searching", "waited": round(now - t["created"]), "v": t["v"]}
        offer = t["offer"]
        if offer is not None:
            other = self.tickets[next(i for i in offer["ids"] if i != ticket_id)]
            info = {"opponent": other["name"], "expires": max(0, round(offer["deadline"] - now))}
            if offer["yes"].get(ticket_id):
                out["pending"] = info    # we said yes: waiting for the other player to confirm
            else:
                out["status"] = "offer"  # waiting for this player's answer
                out["offer"] = info
        return out

    def queue_wait(self, ticket_id, timeout=20, since=None, away=None):
        """Long poll. With `since` (the v last seen) it returns as soon as anything about the search
        changes; without it, only when matched or on timeout. `away` tells the server whether the
        player is on the search page (False) or playing elsewhere (True).

        Only the newest poll of a ticket counts: a request the browser abandoned (the player moved to
        another page) is still waiting here, and must neither flip the away flag back nor swallow a
        match nobody will read. It ends with "superseded" as soon as a newer poll or an /away arrives."""
        deadline = time.monotonic() + timeout
        with self.cond:
            t = self._ticket(ticket_id)
            t["gen"] += 1
            mine = t["gen"]
            if away is not None and t["result"] is None and t["away"] != away:
                self._set_away(ticket_id, away)
            self.cond.notify_all()   # lets an older poll of this ticket notice and end
            while True:
                t = self._ticket(ticket_id)
                now = time.monotonic()
                if t["gen"] != mine:
                    return {"status": "superseded"}
                t["polled"] = now
                if t["result"] is not None:
                    self.tickets.pop(ticket_id, None)
                    return {"status": "matched", **t["result"]}
                if since is not None and t["v"] != since:
                    return self._view(ticket_id, t, now)
                remaining = deadline - now
                if remaining <= 0:
                    return self._view(ticket_id, t, now)
                self.cond.wait(min(remaining, 5))
                self._expire_offers(time.monotonic())

    def queue_away(self, ticket_id, away=True):
        """Sent as the player leaves the search page, so a match found in the gap is offered, not forced."""
        with self.cond:
            t = self._ticket(ticket_id)
            t["gen"] += 1            # retires the poll the page left behind
            t["polled"] = time.monotonic()
            if t["result"] is None and t["away"] != away:
                self._set_away(ticket_id, away)
            self.cond.notify_all()
            return {"away": away}

    def queue_accept(self, ticket_id):
        with self.cond:
            t = self._ticket(ticket_id)
            if t["offer"] is None:
                raise ApiError(409, "no-offer", "That match is no longer available.")
            self._accept(ticket_id)
            return {"accepted": True}

    def queue_decline(self, ticket_id):
        """Not now: both players keep searching, but are not offered each other again."""
        with self.cond:
            t = self._ticket(ticket_id)
            if t["offer"] is None:
                return {"declined": False}
            self._dissolve(t["offer"], avoid=True)
            return {"declined": True}

    def queue_cancel(self, ticket_id):
        with self.cond:
            self._drop_ticket(ticket_id)
            self.cond.notify_all()
            return {"cancelled": True}

    # ---- housekeeping -------------------------------------------------------------------
    def sweep(self):
        """Presence changes, forfeits and expiry. Called about once a second."""
        with self.cond:
            now = time.monotonic()
            for key in [k for k, q in self.hits.items() if not q or now - q[-1] > 60]:
                self.hits.pop(key, None)
            self._drop_stale_tickets(now)
            for room in list(self.rooms.values()):
                if room.status == "waiting":
                    if now - room.created > WAITING_TTL:
                        self._delete(room)
                    continue
                if room.status == "finished":
                    gone = all(s is None or s.left or not s.connected(now) for s in room.seats)
                    if now - (room.finished_at or now) > FINISHED_TTL and gone:
                        self._delete(room)
                        continue
                presence = tuple(bool(s and s.connected(now)) for s in room.seats)
                if room.status == "playing":
                    for i, s in enumerate(room.seats):
                        if presence[i]:
                            s.lost_at = None
                        elif s.lost_at is None:
                            s.lost_at = now
                    for i, s in enumerate(room.seats):
                        if s.lost_at is not None and now - s.lost_at > FORFEIT_GRACE:
                            room.game.resign(i)
                            self._finish(room, "disconnect")
                            break
                if room.status == "playing":
                    # Out of time: play the pawn step that is closest to the goal. A player who is
                    # disconnected keeps their clock stopped (the forfeit timer deals with them).
                    if not presence[room.game.turn]:
                        room.turn_started = now
                    elif room.bank[room.game.turn] - (now - room.turn_started) < -TURN_GRACE:
                        # The player's whole 5 minutes are gone: they lose on time.
                        room.bank[room.game.turn] = 0.0
                        room.game.resign(room.game.turn)
                        self._finish(room, "timeout")
                    elif now - room.turn_started > TURN_SECONDS + TURN_GRACE:
                        mover = room.game.turn
                        room.game.apply(room.game.timeout_move())
                        self._charge(room, mover, now)
                        room.turn_started = now
                        if room.game.winner is not None:
                            self._finish(room)
                        else:
                            self._bump(room)
                if presence != room.presence:
                    room.presence = presence
                    self._bump(room)
                if room.status == "finished" and not any(presence) and now - (room.finished_at or now) > ABANDONED_TTL:
                    self._delete(room)

    def start_sweeper(self):
        if self._sweeper is not None:
            return

        def loop():
            while True:
                time.sleep(1)
                try:
                    self.sweep()
                except Exception:  # never let housekeeping die
                    pass

        self._sweeper = threading.Thread(target=loop, daemon=True, name="quoridor-sweeper")
        self._sweeper.start()


def _counter():
    n = 0
    while True:
        n += 1
        yield n


_seq = _counter()
