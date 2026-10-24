"""End-to-end test of the online API over real HTTP, using the same server as serve.py."""

import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import serve  # noqa: E402
from server import api  # noqa: E402


class Http(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        api.hub.__init__()  # fresh state
        cls.httpd = serve.Server(("127.0.0.1", 0), serve.Handler)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}{serve.PREFIX}/api"
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def call(self, method, path, body=None, token=None, raw=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(self.base + path, data=data, method=method)
        if token:
            req.add_header("X-Seat-Token", token)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read()), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read()), dict(e.headers)

    def test_health_and_headers(self):
        status, body, headers = self.call("GET", "/health")
        self.assertEqual((status, body), (200, {"ok": True}))
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertIn("noindex", headers["X-Robots-Tag"])
        self.assertIn("default-src 'self'", headers["Content-Security-Policy"])

    def test_errors_are_json(self):
        self.assertEqual(self.call("GET", "/nope")[0], 404)
        self.assertEqual(self.call("POST", "/health")[0], 405)
        self.assertEqual(self.call("POST", "/rooms", raw=b"{not json")[:2], (400, {"error": "bad-json", "message": "The request was not valid JSON."}))
        self.assertEqual(self.call("POST", "/rooms", {"username": "x"})[1]["error"], "bad-username")
        self.assertEqual(self.call("POST", "/rooms", raw=b"x" * 9000)[0], 413)

    def test_two_players_over_http(self):
        status, host, _ = self.call("POST", "/rooms", {"username": "Alex"})
        self.assertEqual(status, 200)
        status, guest, _ = self.call("POST", "/rooms/join", {"code": host["code"].lower(), "username": "Sam"})
        self.assertEqual(status, 200)
        self.assertEqual(guest["roomId"], host["roomId"])
        first = host if host["seat"] == 0 else guest
        second = guest if first is host else host
        rid = host["roomId"]

        status, snap, _ = self.call("GET", f"/rooms/{rid}/state", token=first["token"])
        self.assertEqual((status, snap["status"], snap["you"]), (200, "playing", 0))
        self.assertEqual(self.call("GET", f"/rooms/{rid}/state")[0], 403)  # no token

        status, snap, _ = self.call("POST", f"/rooms/{rid}/move", {"move": {"type": "move", "r": 7, "c": 4}}, token=first["token"])
        self.assertEqual((status, snap["game"]["turn"]), (200, 1))
        status, err, _ = self.call("POST", f"/rooms/{rid}/move", {"move": {"type": "move", "r": 7, "c": 4}}, token=first["token"])
        self.assertEqual((status, err["error"]), (409, "not-your-turn"))
        status, err, _ = self.call("POST", f"/rooms/{rid}/move", {"move": {"type": "wall", "o": "h", "r": 9, "c": 0}}, token=second["token"])
        self.assertEqual((status, err["error"]), (422, "out-of-bounds"))

        # The opponent's long poll sees the new version straight away when it is behind.
        status, snap2, _ = self.call("GET", f"/rooms/{rid}/state?since=1", token=second["token"])
        self.assertEqual(snap2["game"]["pawns"][0], [7, 4])
        status, snap3, _ = self.call("POST", f"/rooms/{rid}/resign", token=second["token"])
        self.assertEqual((snap3["status"], snap3["reason"], snap3["game"]["winner"]), ("finished", "resign", 0))

    def test_a_room_for_three_over_http(self):
        status, host, _ = self.call("POST", "/rooms", {"username": "Ana", "variant": "pointrush", "players": 3})
        self.assertEqual(status, 200)
        rid = host["roomId"]
        status, info, _ = self.call("GET", f"/rooms/{rid}")
        self.assertEqual((status, info["variant"], info["players"], info["joined"], info["host"]), (200, "pointrush", 3, 1, "Ana"))
        status, second, _ = self.call("POST", f"/rooms/{rid}/join", {"username": "Ben"})
        self.assertEqual(status, 200)
        status, snap, _ = self.call("GET", f"/rooms/{rid}/state", token=second["token"])
        self.assertEqual((snap["status"], snap["game"]["variant"], snap["game"]["players"], len(snap["players"])), ("waiting", "pointrush", 3, 3))
        status, third, _ = self.call("POST", "/rooms/join", {"code": host["code"], "username": "Cleo"})
        self.assertEqual(status, 200)
        status, snap, _ = self.call("GET", f"/rooms/{rid}/state", token=third["token"])
        self.assertEqual(snap["status"], "playing")
        self.assertEqual(self.call("POST", f"/rooms/{rid}/resign", token=third["token"])[1]["error"], "not-allowed")
        self.assertEqual(self.call("GET", f"/rooms/{rid}")[1]["error"], "full")

    def test_a_custom_room_over_http_and_bad_settings(self):
        custom = {"username": "Ana", "variant": "custom", "options": {"size": 7, "walls": 5, "borrow": True}, "turnSeconds": 0}
        status, host, _ = self.call("POST", "/rooms", custom)
        self.assertEqual(status, 200)
        info = self.call("GET", f"/rooms/{host['roomId']}")[1]
        self.assertEqual((info["options"], info["turnSeconds"]), ({"size": 7, "walls": 5, "borrow": True}, 0))
        for bad in ({"variant": "chess"}, {"variant": "pointrush", "players": 9}, {"variant": "custom", "options": {"size": 8}}):
            status, err, _ = self.call("POST", "/rooms", dict(bad, username="Ana"))
            self.assertEqual((status, err["error"]), (400, "bad-settings"), bad)

    def test_queue_over_http(self):
        status, a, _ = self.call("POST", "/queue", {"username": "Alex"})
        status, b, _ = self.call("POST", "/queue", {"username": "Sam"})
        ra = self.call("GET", f"/queue/{a['ticket']}")[1]
        rb = self.call("GET", f"/queue/{b['ticket']}")[1]
        self.assertEqual((ra["status"], rb["status"]), ("matched", "matched"))
        self.assertEqual(ra["roomId"], rb["roomId"])
        self.assertEqual(self.call("DELETE", f"/queue/{a['ticket']}")[1], {"cancelled": True})


if __name__ == "__main__":
    unittest.main()
