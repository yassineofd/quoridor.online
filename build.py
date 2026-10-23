"""Static site generator for Quoridor Online.

Usage:  python build.py        (writes the finished site to ./public)
Then:   python serve.py        (serves ./public on http://localhost:8000)
"""

import base64
import datetime
import hashlib
import json
import os
import re
import shutil
from html import escape
from pathlib import Path

import i18n
from lib import BASE_PATH, BASE_URL, SITE_NAME, clean_path, icon, icons_js
from pages import all_pages

ROOT = Path(__file__).resolve().parent
# QUORIDOR_BUILD_DIR builds somewhere else (used by the UI tests so ./public is left alone).
CUSTOM_OUT = os.environ.get("QUORIDOR_BUILD_DIR")
OUT = Path(CUSTOM_OUT).resolve() if CUSTOM_OUT else ROOT / "public"
STATIC = ROOT / "static"

NAV = [
    ("play", "/play/", "Play"),
    ("how", "/how-to-play-quoridor/", "How to Play"),
    ("rules", "/quoridor-rules/", "Rules"),
    ("strategy", "/quoridor-strategy/", "Strategy"),
    ("variants", "/variants/", "Variants"),
]

FOOTER_PLAY = [
    ("/play/", "Play Quoridor"),
    ("/play/online/", "Play Online"),
    ("/play/computer/", "Play vs Computer"),
    ("/play/local/", "Play Locally"),
    ("/achievements/", "Achievements"),
]
FOOTER_VARIANTS = [
    ("/variants/wallrush/", "Wallrush"),
    ("/variants/pointrush/", "Pointrush"),
    ("/variants/custom/", "Custom Game"),
]
FOOTER_LEARN = [
    ("/how-to-play-quoridor/", "How to Play"),
    ("/quoridor-rules/", "Quoridor Rules"),
    ("/quoridor-strategy/", "Quoridor Strategy"),
    ("/quoridor-board-game/", "Board Game Guide"),
]
FOOTER_SITE = [
    ("/about/", "About Us"),
    ("/contact/", "Contact Us"),
    ("/privacy-policy/", "Privacy Policy"),
    ("/terms/", "Terms of Use"),
]

# Headers applied by serve.py and written to public/_headers for Netlify/Cloudflare-style hosts.
GA_ID = "G-70NW0H4444"  # Google tag; the matching config call is in static/assets/js/gtag-init.js
BING_VERIFICATION = "68EAA51FF9D2F5EB36A699740C95E884"  # Bing Webmaster Tools meta tag; keep it so the site stays verified
GA_HOSTS = "https://*.google-analytics.com https://*.analytics.google.com https://*.googletagmanager.com"


def _inline_css():
    """The stylesheet, comments and indentation removed, to be placed in each page's <head>."""
    css = (STATIC / "assets" / "css" / "styles.css").read_text(encoding="utf-8")
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return "\n".join(line.strip() for line in css.splitlines() if line.strip())


def _inline_head_js():
    """head.js (language and direction), run inline so it needs no request before the first paint."""
    js = (STATIC / "assets" / "js" / "head.js").read_text(encoding="utf-8")
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    return "\n".join(line.strip() for line in js.splitlines() if line.strip())


def _csp_hash(text):
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode() + "'"


# Render-blocking resources are inlined so the first paint waits for no extra request. The CSP allows
# exactly these two blocks by hash, so no other inline code or style can run.
INLINE_CSS = _inline_css()
INLINE_HEAD_JS = _inline_head_js()
assert "</style" not in INLINE_CSS and "</script" not in INLINE_HEAD_JS

CSP = (
    f"default-src 'self'; script-src 'self' {_csp_hash(INLINE_HEAD_JS)} https://www.googletagmanager.com; "
    f"style-src 'self' {_csp_hash(INLINE_CSS)}; "
    f"img-src 'self' data: {GA_HOSTS}; connect-src 'self' {GA_HOSTS}; "
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


def lang_switch_html():
    """The translate button: a globe with the current language code, opening the list of languages (wired up by i18n.js)."""
    items = "".join(
        f'<li><button type="button" class="lang-option" lang="{code}" data-lang="{code}">{name}</button></li>'
        for code, name, _ in i18n.LANGUAGES
    )
    return (
        '<div class="lang-switch" data-lang-switch>'
        '<button class="btn btn--secondary lang-toggle" type="button" id="lang-toggle" aria-haspopup="true" aria-expanded="false" '
        f'aria-controls="lang-menu" aria-label="Change language">{icon("globe")}<span class="lang-code" data-lang-code data-i18n-skip>EN</span></button>'
        f'<ul class="lang-menu" id="lang-menu" data-i18n-skip hidden>{items}</ul>'
        "</div>"
    )


def theme_toggle_html(extra_class, label_html):
    """Light/dark switch (wired up by site.js). Both suns and moons are in the markup; CSS shows the one for the current theme."""
    name = "" if label_html else ' aria-label="Light theme"'  # the icon-only button needs a name; the row button has visible text
    return (
        f'<button class="theme-toggle {extra_class}" type="button" data-theme-toggle aria-pressed="false"{name}>'
        f'{icon("moon")}{icon("sun")}{label_html}</button>'
    )


def header_html(page):
    items = []
    for key, href, label in NAV:
        cur = ' aria-current="page"' if page.nav_key == key else ""
        items.append(f'<li><a href="{href}"{cur}>{label}</a></li>')
    return f"""
<header class="site-header">
  <div class="container header-bar">
    <a class="brand" href="/" aria-label="Quoridor Online home">
      <img src="/assets/img/logo-mark.png" alt="Quoridor Online logo" width="32" height="32">
      <span class="brand-name" data-i18n-skip>Quoridor <span class="tld">Online</span></span>
    </a>
    <nav class="site-nav" id="site-nav" aria-label="Main">
      <ul>{''.join(items)}</ul>
      <div class="nav-tools">{theme_toggle_html("theme-toggle--row", '<span class="theme-label">Light theme</span><span class="theme-switch" aria-hidden="true"></span>')}</div>
    </nav>
    <div class="header-actions">
      {theme_toggle_html("theme-toggle--icon", "")}
      {lang_switch_html()}
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
        <a class="brand" href="/" aria-label="Quoridor Online home"><img src="/assets/img/logo-mark.png" alt="Quoridor Online logo" width="32" height="32"><span data-i18n-skip>Quoridor <span class="tld">Online</span></span></a>
        <p>A simple place to play and learn the Quoridor strategy game in your browser.</p>
      </div>
      {col('Play', FOOTER_PLAY)}
      {col('Variants', FOOTER_VARIANTS)}
      {col('Learn', FOOTER_LEARN)}
      {col('Site', FOOTER_SITE)}
    </div>
    <div class="footer-legal">
      <p><span data-i18n-skip>&copy; {datetime.date.today().year} {SITE_NAME}.</span> <span>Independent site, not affiliated with or endorsed by the publisher or designer of the Quoridor board game.</span></p>
    </div>
  </div>
</footer>"""


def jsonld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace("</", "<\\/") + "</script>"


def render(page, units=None):
    """The finished HTML of one page. units, if given, collects every translatable text (see i18n.py)."""
    units = units if units is not None else {}
    robots = page.robots or ("index, follow" if page.indexable else "noindex, follow")
    head = []
    if not page.path.startswith("/room/"):  # room URLs are secret invite links: never send them to a third party
        head += [
            f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>',
            '<script src="/assets/js/gtag-init.js" defer></script>',
        ]
    head += [
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title{i18n.head_attr(units, 'text', page.title)}>{escape(page.title)}</title>",
        f'<meta name="description" content="{escape(page.description, quote=True)}"{i18n.head_attr(units, "content", page.description)}>',
        f'<meta name="robots" content="{robots}">',
        '<meta name="theme-color" content="#0B1220">',
        '<meta name="color-scheme" content="dark">',
    ]
    if page.path == "/":  # Bing Webmaster Tools ownership verification: must stay on the home page
        head.append(f'<meta name="msvalidate.01" content="{BING_VERIFICATION}">')
    if page.path.startswith("/room/"):
        head.append('<meta name="referrer" content="no-referrer">')
    if page.canonical and page.url:
        head.append(f'<link rel="canonical" href="{page.url}">')
    head += [
        '<link rel="icon" href="/favicon.ico" sizes="48x48">',
        '<link rel="icon" href="/assets/img/favicon-32.png" type="image/png" sizes="32x32">',
        '<link rel="icon" href="/assets/img/favicon-48.png" type="image/png" sizes="48x48">',
        '<link rel="apple-touch-icon" href="/assets/img/apple-touch-icon.png">',
        '<link rel="manifest" href="/site.webmanifest">',
        f'<meta property="og:site_name" content="{SITE_NAME}">',
        '<meta property="og:type" content="website">',
    ]
    if not page.generic_social:
        head += [
            f'<meta property="og:title" content="{escape(page.title, quote=True)}"{i18n.head_attr(units, "content", page.title)}>',
            f'<meta property="og:description" content="{escape(page.description, quote=True)}"{i18n.head_attr(units, "content", page.description)}>',
            '<meta name="twitter:card" content="summary_large_image">',
        ]
        if BASE_URL:  # absolute URLs are only valid once the real address is known
            head += [
                f'<meta property="og:url" content="{page.url}">',
                f'<meta property="og:image" content="{BASE_URL}{BASE_PATH}/assets/img/og-image.svg">',
                '<meta property="og:image:alt" content="Quoridor Online logo and tagline on a deep navy background">',
            ]
    head += [f"<style>{INLINE_CSS}</style>", f"<script>{INLINE_HEAD_JS}</script>"]

    schema = list(page.schema)
    if BASE_URL and page.indexable and page.breadcrumbs:
        crumbs = [("Home", "/")] + list(page.breadcrumbs)
        schema.append({
            "@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": n, "item": BASE_URL + BASE_PATH + clean_path(p)}
                for i, (n, p) in enumerate(crumbs)
            ],
        })
        schema.append({"@context": "https://schema.org", "@type": "WebPage", "name": page.title, "url": page.url, "description": page.description})
    head += [jsonld(s) for s in schema]

    scripts = ["/assets/js/i18n-en.js", "/assets/js/i18n.js", "/assets/js/site.js"] + page.scripts
    script_tags = "".join(f'<script src="{s}" defer></script>' for s in scripts)
    body = (
        '<a class="skip-link" href="#main">Skip to main content</a>\n'
        + header_html(page)
        + '\n<main id="main" tabindex="-1">\n' + page.body + "\n</main>\n"
        + footer_html()
    )
    html = (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n' + "\n".join(head) + "\n</head>\n<body>\n"
        + i18n.tag_html(body, units) + "\n" + script_tags + "\n</body>\n</html>\n"
    )
    return localize_urls(html, page)


def localize_urls(html, page):
    """Write internal URLs as root-relative links ("/play", "/assets/css/..."), without the trailing slash.

    Pages are authored with root-relative URLs ("/play/"); this drops the trailing slash and adds
    site.json's base_path in front, so a site served from a sub-folder still resolves ("/me/quoridor/play").
    The home page stays "/" (or the base_path plus "/").
    """
    def rewrite(m):
        path, tail = re.match(r"([^?#]*)(.*)", m.group(2)).groups()
        path = path.rstrip("/")
        return f'{m.group(1)}="{BASE_PATH}{"/" + path if path else "/"}{tail}"'

    return re.sub(r'\b(href|src|action)="/(?!/)([^"]*)"', rewrite, html)


def out_path(page):
    if page.out_file:
        return OUT / page.out_file
    rel = page.path.strip("/")
    return OUT / rel / "index.html" if rel else OUT / "index.html"


def main():
    if OUT.exists():
        assert CUSTOM_OUT or OUT.resolve().parent == ROOT, "refusing to delete unexpected directory"
        shutil.rmtree(OUT)
    shutil.copytree(STATIC, OUT)
    (OUT / "assets" / "js" / "icons.js").write_text(icons_js(), encoding="utf-8")

    pages = all_pages()
    units = {}
    for page in pages:
        dest = out_path(page)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(render(page, units), encoding="utf-8")

    # Translations: one file per language, loaded by the browser only when that language is chosen.
    (OUT / "assets" / "js" / "i18n-en.js").write_text(i18n.english_js_file(), encoding="utf-8")
    (OUT / "assets" / "i18n").mkdir(parents=True, exist_ok=True)
    for lang in i18n.TRANSLATED:
        cat = i18n.catalog(lang, units)
        missing = (set(units) | set(i18n.js_english())) - set(cat["p"]) - set(cat["j"])
        if missing:
            print(f"  note: {len(missing)} texts have no {lang} translation yet (they show in English); see: python i18n.py status")
        (OUT / "assets" / "i18n" / f"{lang}.json").write_text(json.dumps(cat, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

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

    # Vercel reads vercel.json from the repo root: serve ./public as-is (no build step needed on the host).
    vercel = {
        "framework": None,
        "buildCommand": None,
        "outputDirectory": "public",
        "trailingSlash": False,
        "rewrites": [{"source": "/room/:id", "destination": "/room/index.html"}],
        "headers": [
            {"source": "/(.*)", "headers": [{"key": k, "value": v} for k, v in SECURITY_HEADERS.items()]},
            {"source": "/room/(.*)", "headers": [{"key": k, "value": v} for k, v in ROOM_HEADERS.items()]},
        ],
    }
    (ROOT / "vercel.json").write_text(json.dumps(vercel, indent=2) + "\n", encoding="utf-8")

    where = f"{BASE_URL}{BASE_PATH}" or "(no site_url set yet)"
    print(f"Built {len(pages)} pages -> {OUT}\nSite address: {where}")


if __name__ == "__main__":
    main()
