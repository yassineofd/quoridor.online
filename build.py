"""Static site generator for Quoridor Online.

Usage:  python build.py        (writes the finished site to ./public)
Then:   python serve.py        (serves ./public on http://localhost:8000)
"""

import datetime
import json
import re
import shutil
from html import escape
from pathlib import Path

from lib import BASE_PATH, BASE_URL, SITE_NAME, icon
from pages import all_pages

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "public"
STATIC = ROOT / "static"

NAV = [
    ("home", "/", "Home"),
    ("play", "/play/", "Play"),
    ("how", "/how-to-play-quoridor/", "How to Play"),
    ("rules", "/quoridor-rules/", "Rules"),
    ("strategy", "/quoridor-strategy/", "Strategy"),
    ("about", "/about/", "About Us"),
]

FOOTER_LEARN = [
    ("/how-to-play-quoridor/", "How to Play"),
    ("/quoridor-rules/", "Quoridor Rules"),
    ("/quoridor-strategy/", "Quoridor Strategy"),
    ("/quoridor-board-game/", "Quoridor Board Game"),
]
FOOTER_SITE = [("/about/", "About Us"), ("/contact/", "Contact Us")]
FOOTER_LEGAL = [("/privacy-policy/", "Privacy Policy"), ("/terms/", "Terms of Use")]

# Headers applied by serve.py and written to public/_headers for Netlify/Cloudflare-style hosts.
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "base-uri 'self'; form-action 'self'; frame-ancestors 'none'; object-src 'none'"
)
SECURITY_HEADERS = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "DENY",
}
ROOM_HEADERS = {
    "X-Robots-Tag": "noindex, nofollow, noarchive",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


def header_html(page):
    items = []
    for key, href, label in NAV:
        cur = ' aria-current="page"' if page.nav_key == key else ""
        items.append(f'<li><a href="{href}"{cur}>{label}</a></li>')
    return f"""
<header class="site-header">
  <div class="container header-bar">
    <a class="brand" href="/" aria-label="Quoridor Online home">
      <img src="/assets/img/logo-mark.svg" alt="" width="32" height="32">
      <span class="brand-name">Quoridor <span class="tld">Online</span></span>
    </a>
    <nav class="site-nav" id="site-nav" aria-label="Main">
      <ul>{''.join(items)}</ul>
    </nav>
    <div class="header-actions">
      <a class="btn btn--primary" href="/play/">Play Now</a>
      <button class="btn btn--secondary menu-toggle" id="menu-toggle" type="button" aria-expanded="false" aria-controls="site-nav">{icon('menu')} Menu</button>
    </div>
  </div>
</header>"""


def footer_html():
    def col(title, links):
        li = "".join(f'<li><a href="{h}">{t}</a></li>' for h, t in links)
        return f'<div><h2>{title}</h2><ul>{li}</ul></div>'

    return f"""
<footer class="site-footer">
  <div class="container">
    <div class="footer-grid">
      <div class="footer-brand">
        <a class="brand" href="/" aria-label="Quoridor Online home"><img src="/assets/img/logo-mark.svg" alt="" width="32" height="32"><span>Quoridor <span class="tld">Online</span></span></a>
        <p>A simple place to play and learn the Quoridor strategy game in your browser.</p>
      </div>
      {col('Learn', FOOTER_LEARN)}
      {col('Site', FOOTER_SITE)}
      {col('Legal', FOOTER_LEGAL)}
    </div>
    <div class="footer-legal">
      <p>&copy; {datetime.date.today().year} {SITE_NAME}. Independent site, not affiliated with or endorsed by the publisher or designer of the Quoridor board game.</p>
    </div>
  </div>
</footer>"""


def jsonld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace("</", "<\\/") + "</script>"


def render(page):
    robots = page.robots or ("index, follow" if page.indexable else "noindex, follow")
    head = [
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{escape(page.title)}</title>",
        f'<meta name="description" content="{escape(page.description, quote=True)}">',
        f'<meta name="robots" content="{robots}">',
        '<meta name="theme-color" content="#0B1220">',
        '<meta name="color-scheme" content="dark">',
    ]
    if page.path.startswith("/room/"):
        head.append('<meta name="referrer" content="no-referrer">')
    if page.canonical and page.url:
        head.append(f'<link rel="canonical" href="{page.url}">')
    head += [
        '<link rel="icon" href="/assets/img/favicon.svg" type="image/svg+xml">',
        '<link rel="manifest" href="/site.webmanifest">',
        f'<meta property="og:site_name" content="{SITE_NAME}">',
        '<meta property="og:type" content="website">',
    ]
    if not page.generic_social:
        head += [
            f'<meta property="og:title" content="{escape(page.title, quote=True)}">',
            f'<meta property="og:description" content="{escape(page.description, quote=True)}">',
            '<meta name="twitter:card" content="summary_large_image">',
        ]
        if BASE_URL:  # absolute URLs are only valid once the real address is known
            head += [
                f'<meta property="og:url" content="{page.url}">',
                f'<meta property="og:image" content="{BASE_URL}{BASE_PATH}/assets/img/og-image.svg">',
                '<meta property="og:image:alt" content="Quoridor Online logo and tagline on a deep navy background">',
            ]
    head += ['<link rel="stylesheet" href="/assets/css/styles.css">', '<script src="/assets/js/head.js"></script>']

    schema = list(page.schema)
    if BASE_URL and page.indexable and page.breadcrumbs:
        crumbs = [("Home", "/")] + list(page.breadcrumbs)
        schema.append({
            "@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": n, "item": BASE_URL + BASE_PATH + p}
                for i, (n, p) in enumerate(crumbs)
            ],
        })
        schema.append({"@context": "https://schema.org", "@type": "WebPage", "name": page.title, "url": page.url, "description": page.description})
    head += [jsonld(s) for s in schema]

    scripts = ["/assets/js/site.js"] + page.scripts
    script_tags = "".join(f'<script src="{s}" defer></script>' for s in scripts)
    html = (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n' +"\n".join(head) + "\n</head>\n<body>\n"
        '<a class="skip-link" href="#main">Skip to main content</a>\n'
        + header_html(page)
        + '\n<main id="main" tabindex="-1">\n' + page.body + "\n</main>\n"
        + footer_html() + "\n" + script_tags + "\n</body>\n</html>\n"
    )
    return localize_urls(html, page)


def localize_urls(html, page):
    """Make internal URLs independent of the domain and of any sub-folder.

    Pages are written with root-relative URLs ("/play/"). Each page rewrites them relative to its
    own location ("../play/"), so the same files work on any host, domain or sub-folder with no
    configuration. The 404 page is the exception: a host serves it at whatever URL was missing,
    so it has no stable depth and uses site.json's base_path instead.
    """
    if page.http_status == 404:
        prefix = BASE_PATH + "/"
    else:
        depth = len([s for s in page.path.split("/") if s])
        prefix = "../" * depth if depth else "./"
    return re.sub(r'\b(href|src|action)="/(?!/)', lambda m: f'{m.group(1)}="{prefix}', html)


def out_path(page):
    if page.out_file:
        return OUT / page.out_file
    rel = page.path.strip("/")
    return OUT / rel / "index.html" if rel else OUT / "index.html"


def main():
    if OUT.exists():
        assert OUT.resolve().parent == ROOT, "refusing to delete unexpected directory"
        shutil.rmtree(OUT)
    shutil.copytree(STATIC, OUT)

    pages = all_pages()
    for page in pages:
        dest = out_path(page)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(render(page), encoding="utf-8")

    # Sitemap: canonical, indexable public pages only. No rooms, tokens, or noindex pages.
    urls = [p for p in pages if (p.in_sitemap if p.in_sitemap is not None else p.indexable)]
    # Sitemaps need absolute URLs, so none is written until site_url is set in site.json.
    robots = f"User-agent: *\nAllow: /\nDisallow: {BASE_PATH}/room/\nDisallow: {BASE_PATH}/api/\nDisallow: {BASE_PATH}/ws/\n"
    if BASE_URL:
        sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        sm += [f"  <url><loc>{p.url}</loc></url>" for p in urls]
        sm.append("</urlset>")
        (OUT / "sitemap.xml").write_text("\n".join(sm) + "\n", encoding="utf-8")
        robots += f"\nSitemap: {BASE_URL}{BASE_PATH}/sitemap.xml\n"
    (OUT / "robots.txt").write_text(robots, encoding="utf-8")

    # Host config files (ignored by hosts that don't use them).
    (OUT / ".nojekyll").write_text("", encoding="utf-8")  # GitHub Pages: serve every file as-is
    if not BASE_PATH:  # Netlify / Cloudflare Pages: any /room/<id>/ shows the room shell
        (OUT / "_redirects").write_text("/room/*  /room/index.html  200\n", encoding="utf-8")

    hdr = ["/*"] + [f"  {k}: {v}" for k, v in SECURITY_HEADERS.items()] + ["", "/room/*"] + [f"  {k}: {v}" for k, v in ROOM_HEADERS.items()]
    (OUT / "_headers").write_text("\n".join(hdr) + "\n", encoding="utf-8")

    where = f"{BASE_URL}{BASE_PATH}" or "(no site_url set yet)"
    print(f"Built {len(pages)} pages -> {OUT}\nSite address: {where}")


if __name__ == "__main__":
    main()
