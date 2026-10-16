"""Local dev/preview server for the built site (./public).

Usage:  python serve.py [port]       (default port 8000)

Behaves like a production host should:
  * unknown URLs return the branded 404 page with a real HTTP 404 status
  * /room/<anything>/ resolves to the room app shell (200) with noindex headers
  * directories get a trailing-slash 301, and security headers are sent on every response
"""

import mimetypes
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from build import ROOM_HEADERS, SECURITY_HEADERS
from lib import BASE_PATH

# SERVE_PREFIX lets you test that the site works from any sub-folder, whatever site.json says.
PREFIX = os.environ.get("SERVE_PREFIX", BASE_PATH).rstrip("/")

PUBLIC = (Path(__file__).resolve().parent / "public").resolve()
mimetypes.add_type("image/svg+xml", ".svg")
mimetypes.add_type("application/manifest+json", ".webmanifest")
ROOM_RE = re.compile(r"^/room/[A-Za-z0-9_-]{1,64}/?$")


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

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        url = urlsplit(self.path)
        path = unquote(url.path)

        if PREFIX:  # serve under a sub-folder, the way a project host would
            if path in ("/", PREFIX):
                self.send_response(301)
                self.send_header("Location", PREFIX + "/")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if not path.startswith(PREFIX + "/"):
                return self._not_found()
            path = path[len(PREFIX):]

        if re.match(r"^/room/[A-Za-z0-9_-]{1,64}$", path):  # relative URLs need the trailing slash
            self.send_response(301)
            self.send_header("Location", PREFIX + path + "/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if ROOM_RE.match(path):
            return self._file(PUBLIC / "room" / "index.html", 200, ROOM_HEADERS)

        if path.startswith("/room/"):
            return self._not_found()  # the room shell is only reachable via /room/<id>/

        target = (PUBLIC / path.lstrip("/")).resolve()
        if PUBLIC != target and PUBLIC not in target.parents:
            return self._not_found()

        if target.is_dir():
            if not path.endswith("/"):
                self.send_response(301)
                self.send_header("Location", PREFIX + path + "/" + (f"?{url.query}" if url.query else ""))
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            index = target / "index.html"
            if index.is_file():
                return self._file(index)
            return self._not_found()

        # Don't expose the 404 template itself or hosting config as pages.
        if target.is_file() and target.name not in ("404.html", "_headers"):
            return self._file(target)
        return self._not_found()

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    if not PUBLIC.exists():
        sys.exit("public/ not found. Run: python build.py")
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Serving {PUBLIC} at http://localhost:{port}{PREFIX}/  (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
