"""Build-time side of the site's translation system (the browser side is static/assets/js/i18n.js).

How it works
  * build.py runs every page through tag_html(). Each piece of visible text (a heading, paragraph, list item,
    button label ...) gets a data-i18n="<id>" attribute, and each translatable attribute (aria-label, title,
    alt, placeholder) gets data-i18n-attr="<attr>:<id>". The id is a short hash of the English text.
  * Translations live in translations/<lang>.txt, one "<id>|<translation>" per line. Messages that JavaScript builds
    at run time (the game screen, errors) use "<key>|<translation>" with the keys listed in translations/js-en.json.
  * build.py writes public/assets/i18n/<lang>.json. The browser loads the one for the chosen language and swaps
    the text in. English needs no file: it is the page itself.
  * Nothing about the language ever reaches the game server, so people playing in different languages share
    one matchmaking pool and the same rooms.

Commands
  python i18n.py status          how complete each language is
  python i18n.py missing es      the untranslated entries of one language as "id|English" lines (to translate)
  python i18n.py lint            find broken links, tags or {parameters} in translations
  python i18n.py check           exit 1 if any language is incomplete, has unused entries or fails lint (also run by check.py)
"""

import hashlib
import html
import json
import os
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIR = ROOT / "translations"

# code, name in its own language, text direction
LANGUAGES = [
    ("en", "English", "ltr"),
    ("es", "Español", "ltr"),
    ("fr", "Français", "ltr"),
    ("de", "Deutsch", "ltr"),
    ("ar", "العربية", "rtl"),
    ("ru", "Русский", "ltr"),
    ("zh", "中文", "ltr"),
]
TRANSLATED = [code for code, _, _ in LANGUAGES if code != "en"]

TRANS_ATTRS = ("aria-label", "title", "alt", "placeholder", "aria-roledescription")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
# Elements whose markup is kept out of the text that gets translated: the browser puts the original
# element back where the placeholder is, so icons and form fields keep their state.
PLACEHOLDERS = {"svg", "input", "img"}
OPAQUE = {"script", "style", "svg"}
SKIP_ATTR = "data-i18n-skip"  # on an element whose text must stay as it is (brand name, text scripts fill in)


def unit_id(kind, key):
    return hashlib.sha1(f"{kind}:{key}".encode("utf-8")).hexdigest()[:6]


def squash(text):
    return re.sub(r"\s+", " ", text).strip()


def has_words(text):
    """True if the text has something to translate (not just symbols, numbers or an email address)."""
    plain = html.unescape(re.sub(r"<[^>]+>", " ", text))
    if re.fullmatch(r"\S+@\S+", plain.strip()):
        return False
    return re.search(r"[^\W\d_]{2,}", plain) is not None


# ---------------------------------------------------------------- a tiny HTML tree that round-trips
class Node:
    __slots__ = ("tag", "attrs", "start", "children", "self_closing")

    def __init__(self, tag, attrs, start, self_closing=False):
        self.tag, self.attrs, self.start, self.self_closing = tag, dict(attrs), start, self_closing
        self.children = []  # str (raw text, entities untouched) | Node


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.root = Node("#root", [], "")
        self.stack = [self.root]

    def _add(self, child):
        self.stack[-1].children.append(child)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, [(k, v if v is not None else "") for k, v in attrs], self.get_starttag_text())
        self._add(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self._add(Node(tag, [(k, v if v is not None else "") for k, v in attrs], self.get_starttag_text(), True))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self._add(data)

    def handle_entityref(self, name):
        self._add(f"&{name};")

    def handle_charref(self, name):
        self._add(f"&#{name};")

    def handle_comment(self, data):
        self._add(f"<!--{data}-->")


def parse(markup):
    tree = Tree()
    tree.feed(markup)
    tree.close()
    return tree.root


def serialize(node, key=False):
    """Back to markup. key=True builds the text that gets translated (placeholders instead of icons and fields)."""
    if isinstance(node, str):
        return node
    if node.tag == "#root":
        return "".join(serialize(c, key) for c in node.children)
    if key and node.tag in PLACEHOLDERS:
        return f"<{node.tag}/>"
    if node.tag in VOID or node.self_closing:
        return node.start
    return node.start + "".join(serialize(c, key) for c in node.children) + f"</{node.tag}>"


def inner(node):
    return squash("".join(serialize(c, True) for c in node.children))


def with_attr(start, extra):
    """Add attributes to a raw start tag."""
    if start.endswith("/>"):
        return start[:-2].rstrip() + " " + extra + "/>"
    return start[:-1] + " " + extra + ">"


# ---------------------------------------------------------------- tagging
def tag_html(markup, units):
    """Returns the markup with data-i18n attributes added. units collects {id: (kind, text)}:
    kind "h" = markup of an element's contents, "a" = plain text of an attribute (or <title>)."""
    root = parse(markup)

    def register(kind, key):
        uid = unit_id(kind, key)
        if uid in units and units[uid] != (kind, key):
            raise RuntimeError(f"i18n id collision on {uid}: {units[uid]!r} vs {(kind, key)!r}")
        units[uid] = (kind, key)
        return uid

    def visit(node):
        if isinstance(node, str) or node.tag in ("script", "style") or SKIP_ATTR in node.attrs:
            return
        extra = []
        attr_ids = []
        for a in TRANS_ATTRS:
            v = squash(node.attrs.get(a, ""))
            if v and has_words(v):
                attr_ids.append(f"{a}:{register('a', v)}")
        if attr_ids:
            extra.append('data-i18n-attr="' + ",".join(attr_ids) + '"')
        if node.tag in OPAQUE:
            if extra:
                node.start = with_attr(node.start, " ".join(extra))
            return
        direct = any(isinstance(c, str) and re.sub(r"&\w+;|&#\w+;|\s", "", c) for c in node.children)
        if direct:
            key = inner(node)
            if has_words(key):
                extra.append(f'data-i18n="{register("h", key)}"')
        if extra:
            node.start = with_attr(node.start, " ".join(extra))
        if not direct:
            for c in node.children:
                visit(c)

    for c in root.children:
        visit(c)
    return serialize(root)


def head_attr(units, name, text):
    """Attribute for a <title>/<meta> whose English text is translated: data-i18n-attr="<name>:<id>"."""
    text = squash(text)
    if not text or not has_words(text):
        return ""
    uid = unit_id("a", text)
    units[uid] = ("a", text)
    return f' data-i18n-attr="{name}:{uid}"'


# ---------------------------------------------------------------- translation files
def js_english():
    return json.loads((DIR / "js-en.json").read_text(encoding="utf-8"))


def load(lang):
    """{id or js key: translation} from translations/<lang>.txt."""
    path = DIR / f"{lang}.txt"
    out = {}
    if not path.exists():
        return out
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        key, sep, text = line.partition("|")
        if not sep:
            raise ValueError(f"{path.name}:{n}: expected 'id|translation'")
        if key in out:
            raise ValueError(f"{path.name}:{n}: duplicate entry {key}")
        out[key] = text.strip()
    return out


def is_page_id(key):
    return re.fullmatch(r"[0-9a-f]{6}", key) is not None


def catalog(lang, units):
    """What the browser downloads for one language: page text ("p") and run-time messages ("j")."""
    t = load(lang)
    return {
        "p": {k: v for k, v in t.items() if is_page_id(k) and k in units},
        "j": {k: v for k, v in t.items() if not is_page_id(k)},
    }


def english_js_file():
    return (
        "/* Generated by build.py from translations/js-en.json. Do not edit. */\n"
        "window.QuoridorI18nEn = " + json.dumps(js_english(), ensure_ascii=False, indent=1) + ";\n"
    )


# ---------------------------------------------------------------- completeness
def gather_units():
    """Every translatable unit of the whole site, for both the online-on and online-off builds."""
    units = {}
    for flag in ("0", "1"):
        env = dict(os.environ, QUORIDOR_ONLINE=flag, PYTHONIOENCODING="utf-8")
        out = subprocess.run([sys.executable, str(ROOT / "i18n.py"), "_dump"], env=env, capture_output=True, check=True, cwd=ROOT).stdout
        for uid, (kind, key) in json.loads(out.decode("utf-8")).items():
            units[uid] = (kind, key)
    return units


def _dump():
    from build import render
    from pages import all_pages
    units = {}
    for page in all_pages():
        render(page, units)
    print(json.dumps(units, ensure_ascii=False))


def problems(units=None):
    """{lang: (missing ids, unused ids)} plus the JS keys; empty lists mean the language is complete."""
    units = units if units is not None else gather_units()
    wanted = set(units) | set(js_english())
    result = {}
    for lang in TRANSLATED:
        have = set(load(lang))
        result[lang] = (sorted(wanted - have), sorted(have - wanted))
    return result, units


def lint(units=None):
    """Mistakes a translator can make that the page would not show: lost or changed links and tags, lost icons,
    changed {parameters}. Returns a list of "lang id: what" lines."""
    units = units if units is not None else gather_units()
    english = js_english()
    out = []

    def tags(text):
        return sorted(re.findall(r"<([a-z0-9]+)", text))

    def hrefs(text):
        return sorted(re.findall(r'(?:href|src)="([^"]*)"', text))

    for lang in TRANSLATED:
        for key, text in load(lang).items():
            if not text:
                out.append(f"{lang} {key}: empty")
            elif key in units:
                kind, source = units[key]
                if kind == "h":
                    if tags(text) != tags(source):
                        out.append(f"{lang} {key}: tags differ: {tags(source)} vs {tags(text)}")
                    elif hrefs(text) != hrefs(source):
                        out.append(f"{lang} {key}: links differ: {hrefs(source)} vs {hrefs(text)}")
                elif "<" in text:
                    out.append(f"{lang} {key}: markup in a plain-text entry")
            elif key in english:
                if sorted(re.findall(r"\{(\w+)\}", text)) != sorted(re.findall(r"\{(\w+)\}", english[key])):
                    out.append(f"{lang} {key}: parameters differ: {english[key]!r} vs {text!r}")
    return out


def main(argv):
    if len(argv) >= 2 and argv[1] == "_dump":
        return _dump()
    cmd = argv[1] if len(argv) > 1 else "status"
    result, units = problems()
    english = js_english()
    if cmd == "missing":
        lang = argv[2]
        missing = set(result[lang][0])
        for key in [k for k in units if k in missing] + [k for k in english if k in missing]:  # page order, then messages
            print(f"{key}|{units[key][1] if key in units else english[key]}")
        return 0
    bad = False
    if cmd == "lint":
        found = lint(units)
        print(chr(10).join(found) or "no problems found")
        return 1 if found else 0
    print(f"{len(units)} page texts + {len(english)} messages")
    for lang, (missing, unused) in result.items():
        print(f"  {lang}: {len(missing)} missing, {len(unused)} unused")
        bad |= bool(missing or unused)
        if cmd == "check":
            for k in missing[:10]:
                print(f"     missing {k}: {(units[k][1] if k in units else english[k])[:80]}")
            for k in unused[:10]:
                print(f"     unused  {k}")
    if cmd == "check":
        found = lint(units)
        print(chr(10).join(found) or "lint: no problems found")
        bad |= bool(found)
    return 1 if (cmd == "check" and bad) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
