"""Translation system: tagging of pages, completeness of every language, and language-neutral online play.

Fast tests, no browser. The browser side (switching, right-to-left, two players in different languages) is in tests/test_ui.py.
"""

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import i18n  # noqa: E402
from server.rooms import ApiError, Hub, clean_username, valid_username  # noqa: E402


class Tagging(unittest.TestCase):
    def tag(self, markup):
        units = {}
        return i18n.tag_html(markup, units), units

    def test_text_blocks_get_an_id_and_keep_their_markup(self):
        out, units = self.tag('<p class="x">Hello <a href="/play/">world</a></p>')
        self.assertRegex(out, r'<p class="x" data-i18n="[0-9a-f]{6}">Hello <a href="/play/">world</a></p>')
        self.assertEqual([k for _, k in units.values()], ['Hello <a href="/play/">world</a>'])

    def test_icons_and_fields_become_placeholders(self):
        _, units = self.tag('<button>Go <svg viewBox="0 0 1 1"><path d="M0 0"/></svg></button><label><input type="checkbox"> Remember me</label>')
        self.assertEqual(sorted(k for _, k in units.values()), ["<input/> Remember me", "Go <svg/>"])

    def test_attributes_and_skipped_elements(self):
        out, units = self.tag('<nav aria-label="Main menu"><a href="/">Home</a></nav><span data-i18n-skip>Quoridor</span><p>2026</p>')
        self.assertIn('data-i18n-attr="aria-label:', out)
        self.assertEqual(sorted(k for _, k in units.values()), ["Home", "Main menu"])  # no brand name, no bare number

    def test_whitespace_does_not_change_the_id(self):
        a, _ = self.tag("<p>Two\n   words</p>")
        b, _ = self.tag("<p>Two words</p>")
        self.assertEqual(re.search(r'data-i18n="(\w+)"', a).group(1), re.search(r'data-i18n="(\w+)"', b).group(1))

    def test_output_is_otherwise_unchanged(self):
        src = '<div class="a"><p>Text &hellip; here</p><br><img src="/x.png" alt=""></div>'
        out, _ = self.tag(src)
        self.assertEqual(re.sub(r' data-i18n="\w+"', "", out), src)


class Completeness(unittest.TestCase):
    """Every text of the site (with online play on and off) and every script message has every translation."""

    @classmethod
    def setUpClass(cls):
        cls.problems, cls.units = i18n.problems()

    def test_no_language_is_missing_anything(self):
        for lang, (missing, unused) in self.problems.items():
            self.assertEqual(missing, [], f"{lang}: untranslated (python i18n.py missing {lang})")
            self.assertEqual(unused, [], f"{lang}: entries nothing uses any more")

    def test_translations_keep_links_tags_and_parameters(self):
        self.assertEqual(i18n.lint(self.units), [])

    def test_translations_are_really_in_the_language(self):
        scripts = {"ar": ("Arabic", re.compile(r"[؀-ۿ]")), "ru": ("Cyrillic", re.compile(r"[Ѐ-ӿ]")), "zh": ("Chinese", re.compile(r"[一-鿿]"))}
        for lang, (name, pattern) in scripts.items():
            for key, text in i18n.load(lang).items():
                if key in self.units and self.units[key][0] == "h" and re.search(r"[A-Za-z]{4,}", re.sub(r"<[^>]+>|&\w+;", "", self.units[key][1])):
                    body = re.sub(r"<[^>]+>|&\w+;|\{\w+\}", "", text)
                    if len(body) > 40:  # a long English sentence must not have been left as it was
                        self.assertRegex(body, pattern, f"{lang} {key}: no {name} in {text[:60]!r}")

    def test_lint_catches_what_a_translator_can_break(self):
        units = {"aaaaaa": ("h", 'Go <a href="/play/">there</a> <svg/>'), "bbbbbb": ("a", "Close")}
        english = {"game.hello": "Hi {name}, you have {n}"}
        broken = {"aaaaaa": 'Ir <a href="/play/">allí</a>', "bbbbbb": "<b>Cerrar</b>", "game.hello": "Hola {nombre}, tienes {n}"}
        real_load, real_english = i18n.load, i18n.js_english
        i18n.load = lambda lang: dict(broken) if lang == "es" else {}
        i18n.js_english = lambda: english
        try:
            found = i18n.lint(units)
        finally:
            i18n.load, i18n.js_english = real_load, real_english
        self.assertTrue(any("tags differ" in f for f in found), found)           # the icon was lost
        self.assertTrue(any("markup in a plain-text" in f for f in found), found)
        self.assertTrue(any("parameters differ" in f for f in found), found)

    def test_every_message_a_script_asks_for_exists(self):
        english = i18n.js_english()
        asked = set()
        for f in (ROOT / "static" / "assets" / "js").glob("*.js"):
            if f.name in ("i18n.js", "icons.js", "ai.js", "ai-worker.js", "engine.js"):
                continue
            src = f.read_text(encoding="utf-8")
            asked |= set(re.findall(r"""\bt\(\s*'([\w.\-]+)'""", src))
            asked |= set(re.findall(r"""'((?:game|board|play|room|watch|contact)\.\w+)'""", src))
        asked = {k for k in asked if not k.endswith(".")}  # "err." + code is put together at run time
        asked |= {k for k in english if k.startswith("err.")}
        self.assertEqual(sorted(k for k in asked if k not in english), [], "scripts use messages that translations/js-en.json lacks")
        used = {k for k in english if any(k in (f.read_text(encoding="utf-8")) for f in (ROOT / "static" / "assets" / "js").glob("*.js"))}
        self.assertEqual(sorted(k for k in english if k not in used and not k.startswith("err.")), [], "messages no script uses")

    def test_catalog_files_are_written_for_each_language(self):
        for lang in i18n.TRANSLATED:
            cat = i18n.catalog(lang, self.units)
            self.assertGreater(len(cat["p"]), 800)
            self.assertEqual(set(cat["j"]), set(i18n.js_english()))
            json.dumps(cat, ensure_ascii=False)


class LanguageIsNoBarrier(unittest.TestCase):
    """Players meet through the same queue and rooms whatever language or alphabet they use."""

    def hub(self):
        return Hub()

    def test_names_in_any_alphabet(self):
        for name in ("José", "Zoë", "ليلى", "محمد علي", "Иван", "李雷", "Åsa-Marie", "Nguyễn Văn", "दीपक"):
            self.assertTrue(valid_username(name), name)
            self.assertEqual(clean_username(name), name)

    def test_composed_and_decomposed_accents_are_the_same_name(self):
        self.assertEqual(clean_username("José"), "José")

    def test_unsafe_names_are_still_refused(self):
        for bad in ("<b>", "a‮b", "x​x", "a\nb", "a", "x" * 21, "Ann@home", "tab\there"):
            with self.assertRaises(ApiError, msg=repr(bad)):
                clean_username(bad)

    def test_players_with_names_in_different_scripts_are_matched_and_play(self):
        hub = self.hub()
        a = hub.queue_join("1.1.1.1", "ليلى")
        b = hub.queue_join("2.2.2.2", "José")
        ra = hub.queue_wait(a["ticket"], since=None)
        rb = hub.queue_wait(b["ticket"], since=None)
        self.assertEqual((ra["status"], rb["status"]), ("matched", "matched"))
        self.assertEqual(ra["roomId"], rb["roomId"])
        snap = hub.wait_state(ra["roomId"], ra["token"], None)
        self.assertEqual(sorted(p["name"] for p in snap["players"]), ["José", "ليلى"])

    def test_the_wire_carries_codes_not_sentences(self):
        """Snapshots and errors identify what happened by a code, so each client words it in its own language."""
        hub = self.hub()
        host = hub.create_room("1.1.1.1", "Ann")
        hub.join_by_id("2.2.2.2", host["roomId"], "Bea")
        snap = hub.wait_state(host["roomId"], host["token"], None)
        self.assertIn(snap["status"], ("playing", "waiting"))
        self.assertIsNone(snap["reason"])
        with self.assertRaises(ApiError) as cm:
            hub.move("1.1.1.1", host["roomId"], host["token"], {"type": "wall", "o": "h", "r": 99, "c": 99})
        self.assertRegex(cm.exception.code, r"^[a-z\-]+$")


if __name__ == "__main__":
    unittest.main()
