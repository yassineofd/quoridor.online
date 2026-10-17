"""Local dev/preview server for the built site (./public).

Usage:  python serve.py [port]       (default port 8000)

Behaves like a production host should:
  * unknown URLs return the branded 404 page with a real HTTP 404 status
  * /room/<anything> resolves to the room app shell (200) with noindex headers
  * page URLs have no trailing slash (/play/ gets a 301 to /play), and security headers are sent on every response
  * /api/... is the online-play server (rooms, matchmaking): see server/api.py
"""

import json
import mimetypes
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from build import ROOM_HEADERS, SECURITY_HEADERS
from lib import BASE_PATH
from server import api

# SERVE_PREFIX lets you test that the site works from any sub-folder, whatever site.json says.
PREFIX = os.environ.get("SERVE_PREFIX", BASE_PATH).rstrip("/")

PUBLIC = Path(os.environ.get("QUORIDOR_PUBLIC") or (Path(__file__).resolve().parent / "public")).resolve()
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("application/manifest+json", ".webmanifest")
ROOM_RE = re.compile(r"^/room/[A-Za-z0-9_-]{1,64}/?$")  # also matches the trailing-slash form, which redirects


class Server(ThreadingHTTPServer):
    daemon_threads = True      # long-poll requests must not keep the process alive on Ctrl+C
    request_queue_size = 128   # the default backlog of 5 drops connections when a page loads many files at once


class Handler(BaseHTTPRequestHandler):
    server_version = "QuoridorDev/1.0"

    def _send(self, status, body, ctype, extra=None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in SECURITY_HEADERS.items():
            self.send_header(k, v)
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _file(self, path, status=200, extra=None):
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/manifest+json", "image/svg+xml"):
            ctype += "; charset=utf-8"
        self._send(status, path.read_bytes(), ctype, extra)

    def _not_found(self):
        page = PUBLIC / "404.html"
        body = page.read_bytes() if page.exists() else b"404 Not Found"
        self._send(404, body, "text/html; charset=utf-8", {"X-Robots-Tag": "noindex"})

    def _api(self, path):
        """Online-play endpoints. Bodies are tiny JSON; everything is uncached and unindexed."""
        url = urlsplit(self.path)
        body = b""
        if self.command in ("POST", "PUT", "PATCH"):
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = -1
            if length < 0 or length > 8192:
                status, payload = 413, {"error": "too-large", "message": "Request too large."}
                return self._json(status, payload)
            body = self.rfile.read(length) if length else b""
        status, payload = api.dispatch(self.command, path[len("/api"):], parse_qs(url.query), body, self)
        self._json(status, payload)

    def _json(self, status, payload):
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self._send(status, data, "application/json; charset=utf-8",
                   {"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"})

    def _redirect(self, path, query=""):
        self.send_response(301)
        self.send_header("Location", PREFIX + path + (f"?{query}" if query else ""))
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _strip_prefix(self, path):
        """Apply SERVE_PREFIX. Returns the path inside the site, or None if the request was answered."""
        if not PREFIX:
            return path
        if path in ("/", PREFIX):
            self.send_response(301)
            self.send_header("Location", PREFIX + "/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        if not path.startswith(PREFIX + "/"):
            self._not_found()
            return None
        return path[len(PREFIX):]

    def do_POST(self):
        path = self._strip_prefix(unquote(urlsplit(self.path).path))
        if path is None:
            return
        if path.startswith("/api/"):
            return self._api(path)
        self._json(405, {"error": "method-not-allowed", "message": "Method not allowed."})

    do_DELETE = do_POST

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        url = urlsplit(self.path)
        path = unquote(url.path)

        path = self._strip_prefix(path)  # serve under a sub-folder, the way a project host would
        if path is None:
            return
        if path.startswith("/api/"):
            return self._api(path)

        if ROOM_RE.match(path):
            if path.endswith("/"):
                return self._redirect(path.rstrip("/"), url.query)  # one address per page: /room/<id>, never /room/<id>/
            return self._file(PUBLIC / "room" / "index.html", 200, ROOM_HEADERS)

        if path == "/room" or path.startswith("/room/"):
            return self._not_found()  # the room shell is only reachable via /room/<id>

        target = (PUBLIC / path.lstrip("/")).resolve()
        if PUBLIC != target and PUBLIC not in target.parents:
            return self._not_found()

        if target.is_dir():
            if path != "/" and path.endswith("/"):
                return self._redirect(path.rstrip("/"), url.query)  # one address per page: /play, never /play/
            index = target / "index.html"
            if index.is_file():
                return self._file(index)
            return self._not_found()

        # Don't expose the 404 template itself or hosting config as pages.
        if target.is_file() and target.name not in ("404.html", "_headers"):
            return self._file(target)
        return self._not_found()

    def log_message(self, fmt, *args):
        # Room ids and matchmaking tickets act as passwords, so never write them to the log.
        line = re.sub(r"(/(?:api/rooms|api/queue|room)/)[A-Za-z0-9_-]{8,64}", r"\1<id>", fmt % args)
        sys.stderr.write("%s %s\n" % (self.address_string(), line))


def main():
    # Hosting platforms (Render, Railway, ...) pass the port in PORT and need the server reachable from outside.
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", 8000))
    if not PUBLIC.exists():
        sys.exit("public/ not found. Run: python build.py")
    host = os.environ.get("QUORIDOR_HOST") or ("0.0.0.0" if "PORT" in os.environ else "127.0.0.1")
    httpd = Server((host, port), Handler)
    api.hub.start_sweeper()
    print(f"Serving {PUBLIC} at http://localhost:{port}{PREFIX}/  (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
