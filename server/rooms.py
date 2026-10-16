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
from collections import deque

from .engine import Game

USERNAME_RE = re.compile(r"^[A-Za-z0-9 _.\-]{2,20}$")
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I
CODE_LENGTH = 6

# Timing (seconds)
PRESENCE = 15            # a seat counts as connected if it polled within this long (or is polling now)
FORFEIT_GRACE = 60       # a disconnected player forfeits after this long
WAITING_TTL = 30 * 60    # an unjoined room (and its code) expires
FINISHED_TTL = 10 * 60   # finished rooms are kept this long so players can ask for a rematch
ABANDONED_TTL = 5 * 60   # both players gone
QUEUE_STALE = 20         # a matchmaking ticket not polled for this long is dropped
LONG_POLL = 25           # max time a state request waits for news

MAX_ROOMS = 5000
MAX_QUEUE = 500


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def clean_username(value):
    if not isinstance(value, str):
        raise ApiError(400, "bad-username", "Choose a name of 2 to 20 characters.")
    name = value.strip()
    if not USERNAME_RE.match(name):
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
        out = {
            "version": room.version,
            "status": room.status,
            "you": seat_index,
            "players": players,
            "game": room.game.to_dict(),
            "reason": room.reason,
            "rematch": list(room.rematch),
            "forfeitIn": forfeit_in,
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
            mine = {"name": name, "created": now, "polled": now, "result": None, "seq": next(_seq)}
            waiting = [(t["seq"], tid, t) for tid, t in self.tickets.items() if t["result"] is None]
            self.tickets[ticket_id] = mine
            if waiting:
                _, other_id, other = min(waiting)
                room = self._new_room(other["name"])
                guest = Seat(name)
                idx = 1 - room.host
                room.seats[idx] = guest
                self._start(room)
                other["result"] = {"roomId": room.id, "token": room.seats[room.host].token, "seat": room.host}
                mine["result"] = {"roomId": room.id, "token": guest.token, "seat": idx}
                self.cond.notify_all()
            return {"ticket": ticket_id}

    def _drop_stale_tickets(self, now):
        for tid in [t for t, v in self.tickets.items() if (v["result"] is None and now - v["polled"] > QUEUE_STALE) or now - v["created"] > 600]:
            self.tickets.pop(tid, None)

    def queue_wait(self, ticket_id, timeout=20):
        deadline = time.monotonic() + timeout
        with self.cond:
            while True:
                t = self.tickets.get(ticket_id)
                if t is None:
                    raise ApiError(404, "unavailable", "That search is no longer active.")
                t["polled"] = time.monotonic()
                if t["result"] is not None:
                    self.tickets.pop(ticket_id, None)
                    return {"status": "matched", **t["result"]}
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return {"status": "searching", "waited": round(time.monotonic() - t["created"])}
                self.cond.wait(min(remaining, 5))
                t["polled"] = time.monotonic()

    def queue_cancel(self, ticket_id):
        with self.cond:
            self.tickets.pop(ticket_id, None)
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
