"""Shared helpers for the static site generator: config, Page model, icons, board art."""

import json
import os
from dataclasses import dataclass, field
from html import escape
from pathlib import Path

# Deployment settings live in site.json so the site isn't tied to any one domain:
#   site_url  - full origin once you know it, e.g. "https://yourname.github.io" (leave "" until then;
#               canonical URLs, sitemap.xml and absolute Open Graph URLs are skipped while it is empty)
#   base_path - sub-folder the site is served from, e.g. "/quoridor-online" on GitHub Pages project
#               sites; leave "" when the site lives at the root of its host.
_cfg = json.loads((Path(__file__).resolve().parent / "site.json").read_text(encoding="utf-8"))
BASE_URL = _cfg.get("site_url", "").strip().rstrip("/")
BASE_PATH = _cfg.get("base_path", "").strip().rstrip("/")
if BASE_PATH and not BASE_PATH.startswith("/"):
    BASE_PATH = "/" + BASE_PATH
SITE_NAME = "Quoridor Online"

# Online play (matchmaking and private rooms) needs the Python game server in server/ (run by
# serve.py). A static host such as Vercel or GitHub Pages cannot run it, so it is off by default:
# set "online_server": true in site.json only when you deploy serve.py (or the server/ package)
# behind your domain. QUORIDOR_ONLINE=1 forces it on for a local build.
ONLINE_SERVER = bool(_cfg.get("online_server", False)) or os.environ.get("QUORIDOR_ONLINE") == "1"

# Feature flags. Public copy may only describe a feature as available once its flag is True
# (docs/architecture-spec.md, honesty rule). Local and computer play run entirely in the browser.
FEATURES = {
    "online": ONLINE_SERVER,
    "computer": True,
    "local": True,
    "rooms": ONLINE_SERVER,
}

# Spec §1/§11 recommendation: index only /play/ at launch; mode pages stay noindex until
# they carry enough unique copy. Flip to True to index them and add them to the sitemap.
INDEX_MODE_PAGES = False


@dataclass
class Page:
    path: str  # URL path, e.g. "/quoridor-rules/"
    title: str
    description: str
    body: str
    indexable: bool = True
    robots: str | None = None  # explicit robots meta override
    breadcrumbs: list = field(default_factory=list)  # [(label, path), ...] excluding Home
    scripts: list = field(default_factory=list)
    schema: list = field(default_factory=list)  # extra JSON-LD objects
    in_sitemap: bool | None = None  # defaults to indexable
    canonical: bool = True
    out_file: str | None = None  # override output file, e.g. "404.html"
    http_status: int = 200
    generic_social: bool = False  # omit page-specific Open Graph data (private rooms)
    nav_key: str | None = None

    @property
    def url(self):
        """Absolute canonical URL, or None while no site_url is configured."""
        return BASE_URL + BASE_PATH + self.path if BASE_URL else None


# Icons are Lucide (https://lucide.dev, ISC license), copied unchanged from lucide-static 1.59.0.
# Only the inner shapes are stored; icon() adds the shared <svg> wrapper (24x24, 2px round stroke).
_ICONS = {
    "globe": '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>',
    "bot": '<path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><path d="M16 3.128a4 4 0 0 1 0 7.744"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><circle cx="9" cy="7" r="4"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
    "key": '<path d="m2 21 9.6-9.6"/><path d="m7.5 15.5 2.3 2.3a1 1 0 0 1 0 1.4l-2.1 2.1a1 1 0 0 1-1.4 0L4 19"/><circle cx="15.5" cy="7.5" r="5.5"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "alert": '<circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/>',
    "arrow": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    "arrow-left": '<path d="m12 19-7-7 7-7"/><path d="M19 12H5"/>',
    "menu": '<path d="M4 5h16"/><path d="M4 12h16"/><path d="M4 19h16"/>',
    "copy": '<rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
    "smartphone": '<rect width="14" height="20" x="5" y="2" rx="2" ry="2"/><path d="M12 18h.01"/>',
    "userx": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="17" x2="22" y1="8" y2="13"/><line x1="22" x2="17" y1="8" y2="13"/>',
    "layout": '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
    "book": '<path d="M12 5v16"/><path d="M20.001 19A2 2 0 0022 17V5a2 2 0 00-1.999-2L16 3.002A5 5 0 0012 5a5 5 0 00-4-2H4a2 2 0 00-2 2v12a2 2 0 001.999 2H8a5 5 0 014 2 5 5 0 014-2z"/>',
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "move": '<path d="M12 2v20"/><path d="m15 19-3 3-3-3"/><path d="m19 9 3 3-3 3"/><path d="M2 12h20"/><path d="m5 9-3 3 3 3"/><path d="m9 5 3-3 3 3"/>',
    "wall": '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M12 9v6"/><path d="M16 15v6"/><path d="M16 3v6"/><path d="M3 15h18"/><path d="M3 9h18"/><path d="M8 15v6"/><path d="M8 3v6"/>',
    "rotate": '<path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/>',
    "x": '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    "undo": '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5a5.5 5.5 0 0 1-5.5 5.5H11"/>',
    "flag": '<path d="M4 22V4a1 1 0 0 1 .4-.8A6 6 0 0 1 8 2c3 0 5 2 7.333 2q2 0 3.067-.8A1 1 0 0 1 20 4v10a1 1 0 0 1-.4.8A6 6 0 0 1 16 16c-3 0-5-2-8-2a6 6 0 0 0-4 1.528"/>',
    "restart": '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
    "logout": '<path d="m16 17 5-5-5-5"/><path d="M21 12H9"/><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>',
    "login": '<path d="m10 17 5-5-5-5"/><path d="M15 12H3"/><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>',
    "play": '<path d="M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z"/>',
    "plus": '<path d="M5 12h14"/><path d="M12 5v14"/>',
}


_SVG_OPEN = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
)


def icon(name: str) -> str:
    return _SVG_OPEN + _ICONS[name] + "</svg>"


def icons_js() -> str:
    """Browser-side twin of icon(): window.QuoridorIcons.svg(name) returns the same markup, so
    buttons built in game.js use the same Lucide icons as the server-rendered pages."""
    return (
        "/* Generated by build.py from lib.py. Do not edit. Lucide icons (ISC license). */\n"
        "(function (root) {\n  'use strict';\n"
        f"  var OPEN = {json.dumps(_SVG_OPEN)};\n"
        f"  var SHAPES = {json.dumps(_ICONS, indent=2)};\n"
        "  root.QuoridorIcons = {\n"
        "    svg: function (name) { return OPEN + SHAPES[name] + '</svg>'; }\n"
        "  };\n"
        "})(window);\n"
    )


# ---- Board illustration -------------------------------------------------------------
_CELL, _GAP, _PAD = 80, 10, 50
_PITCH = _CELL + _GAP


def board_svg(walls=(), pawns=(), label: str = "", goal_tint: bool = True, marks=(), bad_walls=()) -> str:
    """Minimalist 9x9 board. walls: ("h", r, c) lies below row r across cols c..c+1;
    ("v", r, c) lies right of col c across rows r..r+1. pawns: (row, col, "p1"|"p2").
    P1 is a filled circle, P2 a ring, so the two are never told apart by color alone.
    marks: (row, col, text) squares a pawn can reach, drawn dashed with a letter or number.
    bad_walls: walls in the same format as walls, drawn dashed with a cross to show an illegal placement."""
    size = _PAD * 2 + 9 * _CELL + 8 * _GAP
    out = [
        f'<svg class="board-art" viewBox="0 0 {size} {size}" width="{size}" height="{size}" '
        + (f'role="img" aria-label="{escape(label, quote=True)}"' if label else 'aria-hidden="true" focusable="false"')
        + ' xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{size}" height="{size}" rx="40" fill="#0B1220"/>',
    ]
    for r in range(9):
        for c in range(9):
            x, y = _PAD + c * _PITCH, _PAD + r * _PITCH
            out.append(f'<rect x="{x}" y="{y}" width="{_CELL}" height="{_CELL}" rx="10" fill="#111C30" stroke="#26364F" stroke-width="2"/>')
            if goal_tint and r == 0:
                out.append(f'<rect x="{x}" y="{y}" width="{_CELL}" height="{_CELL}" rx="10" fill="#42D9F5" fill-opacity="0.13"/>')
            if goal_tint and r == 8:
                out.append(f'<rect x="{x}" y="{y}" width="{_CELL}" height="{_CELL}" rx="10" fill="#FFFFFF" fill-opacity="0.08"/>')
    for r, c, text in marks:
        x, y = _PAD + c * _PITCH, _PAD + r * _PITCH
        out.append(f'<rect x="{x}" y="{y}" width="{_CELL}" height="{_CELL}" rx="10" fill="#42D9F5" fill-opacity="0.22" stroke="#42D9F5" stroke-width="4" stroke-dasharray="10 7"/>')
        out.append(f'<text x="{x + _CELL / 2}" y="{y + _CELL / 2 + 14}" text-anchor="middle" font-family="system-ui,sans-serif" font-size="42" font-weight="700" fill="#E8F9FD">{escape(str(text))}</text>')
    for group, bad in ((walls, False), (bad_walls, True)):
        for kind, r, c in group:
            if kind == "h":
                x, y, w, h = _PAD + c * _PITCH, _PAD + r * _PITCH + _CELL - 2, 2 * _CELL + _GAP, _GAP + 4
            else:
                x, y, w, h = _PAD + c * _PITCH + _CELL - 2, _PAD + r * _PITCH, _GAP + 4, 2 * _CELL + _GAP
            if bad:
                out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="#FF8A96" fill-opacity="0.35" stroke="#FF8A96" stroke-width="3" stroke-dasharray="9 6"/>')
                cx, cy = x + w / 2, y + h / 2
                out.append(f'<path d="M{cx - 14} {cy - 14}L{cx + 14} {cy + 14}M{cx + 14} {cy - 14}L{cx - 14} {cy + 14}" stroke="#FF8A96" stroke-width="7" stroke-linecap="round"/>')
            else:
                out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="#5267F2" stroke="#9aa8ff" stroke-width="1.5"/>')
    for r, c, who in pawns:
        cx, cy = _PAD + c * _PITCH + _CELL / 2, _PAD + r * _PITCH + _CELL / 2
        if who == "p1":
            out.append(f'<circle cx="{cx}" cy="{cy}" r="27" fill="#42D9F5"/>')
        else:
            out.append(f'<circle cx="{cx}" cy="{cy}" r="24" fill="#0B1220" stroke="#FFFFFF" stroke-width="9"/>')
    out.append("</svg>")
    return "".join(out)


HERO_WALLS = [("h", 2, 3), ("v", 4, 5), ("h", 5, 1), ("v", 6, 2), ("h", 6, 4), ("v", 2, 6)]
HERO_PAWNS = [(7, 4, "p1"), (1, 4, "p2")]
HERO_ALT = (
    "Illustration of a Quoridor game board: a 9 by 9 grid with a cyan pawn near the bottom, "
    "a white ring pawn near the top, and several indigo barriers placed between squares."
)
