"""Shared helpers for the static site generator: config, Page model, icons, board art."""

import json
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

# Feature flags. Public copy may only describe a feature as available once its flag is True
# (docs/architecture-spec.md, honesty rule). Flip these as each mode is actually implemented.
FEATURES = {
    "online": False,
    "computer": False,
    "local": False,
    "rooms": False,
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


_ICONS = {
    "globe": '<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
    "bot": '<rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><path d="M8 16h.01"/><path d="M16 16h.01"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
    "key": '<circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6"/><path d="m15.5 7.5 3 3L22 7l-3-3"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "alert": '<circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/>',
    "arrow": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    "menu": '<path d="M4 6h16"/><path d="M4 12h16"/><path d="M4 18h16"/>',
    "copy": '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    "smartphone": '<rect x="5" y="2" width="14" height="20" rx="2"/><path d="M12 18h.01"/>',
    "userx": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="m17 8 5 5"/><path d="m22 8-5 5"/>',
    "layout": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/>',
    "book": '<path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/>',
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
}


def icon(name: str) -> str:
    return (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
        + _ICONS[name]
        + "</svg>"
    )


# ---- Board illustration -------------------------------------------------------------
_CELL, _GAP, _PAD = 80, 10, 50
_PITCH = _CELL + _GAP


def board_svg(walls=(), pawns=(), label: str = "", goal_tint: bool = True) -> str:
    """Minimalist 9x9 board. walls: ("h", r, c) lies below row r across cols c..c+1;
    ("v", r, c) lies right of col c across rows r..r+1. pawns: (row, col, "p1"|"p2").
    P1 is a filled circle, P2 a ring, so the two are never told apart by color alone."""
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
    for kind, r, c in walls:
        if kind == "h":
            x, y, w, h = _PAD + c * _PITCH, _PAD + r * _PITCH + _CELL - 2, 2 * _CELL + _GAP, _GAP + 4
        else:
            x, y, w, h = _PAD + c * _PITCH + _CELL - 2, _PAD + r * _PITCH, _GAP + 4, 2 * _CELL + _GAP
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
