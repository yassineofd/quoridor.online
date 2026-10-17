"""HTTP/JSON surface for online play. serve.py mounts this under /api/.

  GET    /api/health
  POST   /api/rooms                      {username}            -> {roomId, code, token, seat}
  POST   /api/rooms/join                 {code, username}      -> {roomId, token, seat}
  GET    /api/rooms/<id>                                       -> {status:"open", host}   (404 / 409 full)
  POST   /api/rooms/<id>/join            {username}            -> {roomId, token, seat}
  GET    /api/rooms/<id>/state?since=N   X-Seat-Token          -> snapshot (waits up to 25 s for news)
  POST   /api/rooms/<id>/move            {move}  X-Seat-Token  -> snapshot
  POST   /api/rooms/<id>/resign          X-Seat-Token          -> snapshot
  POST   /api/rooms/<id>/leave           X-Seat-Token          -> {left:true}
  POST   /api/rooms/<id>/rematch         X-Seat-Token          -> snapshot
  POST   /api/queue                      {username}            -> {ticket}
  GET    /api/queue/<ticket>?v=N&away=0|1                      -> {status:"searching"|"offer"|"matched", v, ...} (waits up to 20 s)
           "offer": a match is waiting for this away player's answer ({offer:{opponent, expires}});
           "searching" + "pending": this player said yes, the other still has to ({pending:{...}})
  POST   /api/queue/<ticket>/away                              -> {away:true}  (left the search page; keep searching)
  POST   /api/queue/<ticket>/accept                            -> {accepted:true}  (409 if the offer is gone)
  POST   /api/queue/<ticket>/decline                           -> {declined:bool}  (keep searching, not with this player)
  DELETE /api/queue/<ticket>                                   -> {cancelled:true}

Seat tokens travel in a header, never in a URL, so they don't end up in logs or referrers.
"""

import json
import os
import re

from .rooms import ApiError, Hub

hub = Hub()

ID = r"([A-Za-z0-9_-]{8,64})"
ROUTES = []


def route(method, pattern):
    rx = re.compile("^" + pattern + "$")

    def deco(fn):
        ROUTES.append((method, rx, fn))
        return fn
    return deco


def client_ip(handler):
    if os.environ.get("QUORIDOR_TRUST_PROXY") == "1":
        fwd = handler.headers.get("X-Forwarded-For", "")
        if fwd:
            return fwd.split(",")[0].strip()
    return handler.client_address[0]


def dispatch(method, path, query, body, handler):
    """Returns (status, payload). Never raises."""
    try:
        for m, rx, fn in ROUTES:
            if m == method:
                match = rx.match(path)
                if match:
                    return 200, fn(Req(handler, query, body), *match.groups())
        if any(rx.match(path) for _, rx, _ in ROUTES):
            raise ApiError(405, "method-not-allowed", "Method not allowed.")
        raise ApiError(404, "not-found", "Not found.")
    except ApiError as e:
        return e.status, {"error": e.code, "message": e.message}
    except Exception:  # a bug must not leak internals
        return 500, {"error": "server-error", "message": "Something went wrong on the server."}


class Req:
    def __init__(self, handler, query, body):
        self.ip = client_ip(handler)
        self.token = handler.headers.get("X-Seat-Token", "")
        self.query = query
        self._body = body

    def json(self):
        if not self._body:
            return {}
        try:
            data = json.loads(self._body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise ApiError(400, "bad-json", "The request was not valid JSON.")
        if not isinstance(data, dict):
            raise ApiError(400, "bad-json", "The request was not valid JSON.")
        return data


@route("GET", "/health")
def health(req):
    return {"ok": True}


@route("POST", "/rooms")
def create_room(req):
    return hub.create_room(req.ip, req.json().get("username"))


@route("POST", "/rooms/join")
def join_by_code(req):
    d = req.json()
    return hub.join_by_code(req.ip, d.get("code"), d.get("username"))


@route("GET", "/rooms/" + ID)
def peek(req, room_id):
    return hub.peek(req.ip, room_id)


@route("POST", "/rooms/" + ID + "/join")
def join_by_id(req, room_id):
    return hub.join_by_id(req.ip, room_id, req.json().get("username"))


@route("GET", "/rooms/" + ID + "/state")
def state(req, room_id):
    since = req.query.get("since", [None])[0]
    try:
        since = int(since) if since is not None else None
    except ValueError:
        since = None
    return hub.wait_state(room_id, req.token, since)


@route("POST", "/rooms/" + ID + "/move")
def move(req, room_id):
    return hub.move(req.ip, room_id, req.token, req.json().get("move"))


@route("POST", "/rooms/" + ID + "/resign")
def resign(req, room_id):
    return hub.resign(room_id, req.token)


@route("POST", "/rooms/" + ID + "/leave")
def leave(req, room_id):
    return hub.leave(room_id, req.token)


@route("POST", "/rooms/" + ID + "/rematch")
def rematch(req, room_id):
    return hub.rematch(room_id, req.token)


@route("POST", "/queue")
def queue_join(req):
    return hub.queue_join(req.ip, req.json().get("username"))


@route("GET", "/queue/" + ID)
def queue_wait(req, ticket):
    try:
        since = int(req.query.get("v", [None])[0])
    except (TypeError, ValueError):
        since = None
    away = req.query.get("away", [None])[0]
    return hub.queue_wait(ticket, since=since, away=None if away is None else away == "1")


@route("POST", "/queue/" + ID + "/away")
def queue_away(req, ticket):
    return hub.queue_away(ticket)


@route("POST", "/queue/" + ID + "/accept")
def queue_accept(req, ticket):
    return hub.queue_accept(ticket)


@route("POST", "/queue/" + ID + "/decline")
def queue_decline(req, ticket):
    return hub.queue_decline(ticket)


@route("DELETE", "/queue/" + ID)
def queue_cancel(req, ticket):
    return hub.queue_cancel(ticket)
