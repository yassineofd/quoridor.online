"""Automated checks against the built site: python build.py && python check.py

Starts the dev server on a spare port and verifies status codes, SEO metadata, internal links,
heading structure, sitemap/robots rules and a few accessibility basics.
"""

import re
import sys
import threading
import urllib.request
import urllib.error
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer
from urllib.parse import urljoin, urlsplit

import serve
from lib import BASE_PATH, BASE_URL

PREFIX = serve.PREFIX

PORT = 8765
BASE = f"http://127.0.0.1:{PORT}"
failures, warnings = [], []


def fail(msg):
    failures.append(msg)
    print("  FAIL", msg)


def warn(msg):
    warnings.append(msg)
    print("  warn", msg)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoRedirect)


def get(path):
    if PREFIX and not path.startswith(PREFIX + "/"):
        path = PREFIX + path
    try:
        r = opener.open(BASE + path)
        return r.status, dict(r.headers), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", "replace")


class Doc(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self._in_title = False
        self.meta, self.links, self.hrefs, self.srcs, self.ids = {}, [], [], [], []
        self.h = []
        self.canonical = None
        self.lang = None
        self.inline_styles = 0
        self.imgs_no_alt = 0
        self._cur_h = None
        self.ld = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "style" in a:
            self.inline_styles += 1
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = a.get("name") or a.get("property")
            if key:
                self.meta[key] = a.get("content", "")
        elif tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href")
        elif tag == "a" and "href" in a:
            self.hrefs.append(a["href"])
        elif tag in ("script", "img") and "src" in a:
            self.srcs.append(a["src"])
            if tag == "img" and "alt" not in a:
                self.imgs_no_alt += 1
            if tag == "script" and a.get("type") == "application/ld+json":
                self.ld += 1
        elif tag == "link" and "href" in a:
            self.srcs.append(a["href"])
        if tag == "script" and a.get("type") == "application/ld+json":
            self.ld += 1
        if re.fullmatch(r"h[1-6]", tag):
            self.h.append(int(tag[1]))

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


class Outline(HTMLParser):
    """Collects the text of h1/h2/h3/summary elements and every link as (text, href)."""

    def __init__(self):
        super().__init__()
        self.text = {"h1": [], "h2": [], "h3": [], "summary": []}
        self.links = []
        self._tag = None
        self._buf = []
        self._href = None
        self._abuf = []

    def handle_starttag(self, tag, attrs):
        if tag in self.text:
            self._tag, self._buf = tag, []
        elif tag == "a":
            self._href, self._abuf = dict(attrs).get("href"), []

    def handle_endtag(self, tag):
        if tag == self._tag:
            self.text[tag].append(" ".join("".join(self._buf).split()))
            self._tag = None
        elif tag == "a" and self._href is not None:
            self.links.append((" ".join("".join(self._abuf).split()), self._href))
            self._href = None

    def handle_data(self, data):
        if self._tag:
            self._buf.append(data)
        if self._href is not None:
            self._abuf.append(data)


def check_home(body):
    """The home page content is a contract: fixed H1, CTAs, H2 sections, FAQ and internal links."""
    from lib import FEATURES
    from pages import HOME_CTAS, HOME_FAQ_QUESTIONS, HOME_H1, HOME_H2S

    main = re.search(r"<main\b.*?</main>", body, re.S)
    if not main:
        fail("home: no <main> element")
        return
    body = main.group(0)
    o = Outline()
    o.feed(body)
    if o.text["h1"] != [HOME_H1]:
        fail(f"home: H1 must be exactly {HOME_H1!r}, found {o.text['h1']}")
    if o.text["h2"] != list(HOME_H2S):
        fail(f"home: H2 sections must be {list(HOME_H2S)} in order, found {o.text['h2']}")
    if o.text["summary"] != list(HOME_FAQ_QUESTIONS):
        fail(f"home: FAQ questions must be {list(HOME_FAQ_QUESTIONS)}, found {o.text['summary']}")

    def path_of(href):
        p = urlsplit(urljoin(PREFIX + "/", href)).path
        return p[len(PREFIX):] if PREFIX and p.startswith(PREFIX) else p

    links = [(t, path_of(h)) for t, h in o.links if not h.startswith(("#", "http", "mailto:"))]
    for label, target in HOME_CTAS:
        if not any(t.startswith(label) and p == target for t, p in links):
            fail(f"home: missing CTA {label!r} -> {target}")
    for target in ("/play/", "/how-to-play-quoridor/", "/quoridor-rules/", "/quoridor-strategy/", "/quoridor-board-game/"):
        if not any(p == target for _, p in links):
            fail(f"home: no internal link to {target}")

    # Only modes that really work may be advertised.
    modes = {"online": ("Play Online", "/play/online/"), "computer": ("Play Against the Computer", "/play/computer/"),
             "local": ("Play Locally", "/play/local/")}
    for feat, (title, target) in modes.items():
        listed = title in o.text["h3"] and any(p == target for _, p in links)
        if FEATURES[feat] != listed:
            fail(f"home: mode {title!r} {'is missing' if FEATURES[feat] else 'is advertised but not live'}")
    if "Coming soon" in body:
        fail("home: must not show 'Coming soon' badges")
    if len(re.findall(r'<svg class="board-art"', body)) < 1:
        fail("home: missing board preview")


def main():
    httpd =ThreadingHTTPServer(("127.0.0.1", PORT), serve.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    serve.Handler.log_message = lambda *a, **k: None

    from pages import all_pages

    pages = all_pages()
    titles, descs, url_status = {}, {}, {}

    print("Status codes and headers")
    for path, want in [("/", 200), ("/play/", 200), ("/nope/", 404), ("/play/nope/", 404), ("/room/", 404),
                       ("/room/AbC123xyz/", 200), ("/about", 301), ("/404.html", 404), ("/_headers", 404),
                       ("/../build.py", 404), ("/%2e%2e/build.py", 404)]:
        status, hdr, body = get(path)
        if status != want:
            fail(f"{path}: expected {want}, got {status}")
    status, hdr, body = get("/room/AbC123xyz/")
    if "noindex" not in hdr.get("X-Robots-Tag", ""):
        fail("room responses must send X-Robots-Tag: noindex")
    status, hdr, body = get("/nope/")
    if "This Page Couldn" not in body:
        fail("404 must show the branded not-found page")
    if "default-src" not in hdr.get("Content-Security-Policy", ""):
        fail("CSP header missing")

    print("Per-page checks")
    for p in pages:
        if p.path == "/room/_/":
            url, label = "/room/AbC123xyz/", "room"
        elif p.path == "/404/":
            url, label = "/nope/", "404"
        else:
            url, label = p.path, p.path
        status, hdr, body = get(url)
        url = PREFIX + url
        want = p.http_status
        if status != want:
            fail(f"{label}: status {status}, expected {want}")
        d = Doc()
        d.feed(body)
        url_status[url] = status

        if d.lang != "en":
            fail(f"{label}: missing lang=en")
        if "width=device-width" not in d.meta.get("viewport", ""):
            fail(f"{label}: missing viewport meta")
        if not d.title.strip():
            fail(f"{label}: empty title")
        if not d.meta.get("description"):
            fail(f"{label}: missing meta description")
        if label != "404":
            root_abs = [h for h in d.hrefs + d.srcs if h.startswith("/") and not h.startswith("//")]
            if root_abs:
                fail(f"{label}: root-absolute URLs would break in a sub-folder: {root_abs[:3]}")
        if d.inline_styles:
            fail(f"{label}: {d.inline_styles} inline style attribute(s) (breaks strict CSP)")
        if d.imgs_no_alt:
            fail(f"{label}: {d.imgs_no_alt} img without alt")
        if len(d.ids) != len(set(d.ids)) and label != "room":
            fail(f"{label}: duplicate ids")
        if len(d.title) > 65:
            warn(f"{label}: title is {len(d.title)} chars (>65)")
        if len(d.meta.get("description", "")) > 165:
            warn(f"{label}: description is {len(d.meta['description'])} chars (>165)")

        if label != "room":
            if d.h.count(1) != 1:
                fail(f"{label}: expected exactly one h1, found {d.h.count(1)}")
            prev = 1
            for lvl in d.h:
                if lvl > prev + 1:
                    fail(f"{label}: heading level jumps h{prev} -> h{lvl}")
                    break
                prev = lvl

        if p.indexable:
            if p.url and d.canonical != p.url:
                fail(f"{label}: canonical {d.canonical!r} != {p.url!r}")
            if not p.url and d.canonical:
                fail(f"{label}: canonical present although no site_url is set")
            if "noindex" in d.meta.get("robots", ""):
                fail(f"{label}: indexable page has noindex")
            titles.setdefault(d.title, []).append(label)
            descs.setdefault(d.meta.get("description"), []).append(label)
        else:
            if "noindex" not in d.meta.get("robots", ""):
                fail(f"{label}: non-indexable page lacks noindex")

        # Links and assets
        for href in d.hrefs + d.srcs:
            if href.startswith(("mailto:", "tel:", "http://", "https://", "data:")):
                continue
            target = urlsplit(urljoin(url, href))
            frag = target.fragment
            if target.path.startswith("/room/") and label in ("/play/create-room/", "/play/join-room/"):
                pass  # preview links to the room shell
            code = 200 if href.startswith("#") else get(target.path)[0]
            if code >= 400:
                if label == "404" and PREFIX != BASE_PATH:
                    warn(f"{label}: {href} needs base_path={PREFIX!r} in site.json (404 pages can't use relative URLs)")
                else:
                    fail(f"{label}: broken link {href} ({code})")
            if frag and target.path == url and frag not in d.ids:
                fail(f"{label}: fragment #{frag} has no target")

    print("Home page contract")
    check_home(get("/")[2])

    for name, store in (("title", titles), ("description", descs)):
        for k, v in store.items():
            if len(v) > 1:
                fail(f"duplicate {name} on {v}")

    print("Sitemap and robots")
    status, _, rb = get("/robots.txt")
    if f"Disallow: {BASE_PATH}/room/" not in rb:
        fail("robots.txt must disallow the room path")
    status, _, sm = get("/sitemap.xml")
    if BASE_URL:
        locs = re.findall(r"<loc>([^<]+)</loc>", sm)
        indexable = {p.url for p in pages if p.indexable}
        if set(locs) != indexable:
            fail(f"sitemap mismatch: extra={set(locs) - indexable}, missing={indexable - set(locs)}")
        for loc in locs:
            if "/room/" in loc or "?" in loc:
                fail(f"sitemap contains private/parameterised URL {loc}")
        if "Sitemap:" not in rb:
            fail("robots.txt must reference the sitemap")
    else:
        print("  (no site_url set: sitemap.xml correctly not generated)")
        if status != 404 or "Sitemap:" in rb:
            fail("with no site_url there must be no sitemap.xml and no Sitemap: line")

    print("Domain independence")
    host = BASE_URL.split("//")[-1].lower()
    for f in serve.PUBLIC.rglob("*"):
        if f.is_file() and f.suffix in (".html", ".js", ".css", ".svg", ".xml", ".txt", ".webmanifest"):
            text = f.read_text(encoding="utf-8").lower()
            if "quoridor.online" in text and host != "quoridor.online":
                fail(f"{f.relative_to(serve.PUBLIC)} mentions quoridor.online")

    httpd.shutdown()
    print(f"\n{len(failures)} failure(s), {len(warnings)} warning(s), {len(pages)} pages checked")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
