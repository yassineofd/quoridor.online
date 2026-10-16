"""Tiny helper: run a local HTML page in headless Edge/Chrome and return the resulting DOM."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/chromium", "/usr/bin/chromium-browser", "/usr/bin/google-chrome",
]


def find_browser():
    for path in _CANDIDATES:
        if os.path.exists(path):
            return path
    for name in ("msedge", "chrome", "chromium", "google-chrome"):
        found = shutil.which(name)
        if found:
            return found
    return None


def dump_dom(url, budget_ms=120000, timeout=600):
    """Load `url`, let scripts run (virtual time unless budget_ms is 0/None), and return the page's final HTML."""
    exe = find_browser()
    if not exe:
        raise FileNotFoundError("no Edge/Chrome found for browser tests")
    with tempfile.TemporaryDirectory() as profile:
        proc = subprocess.run(
            [exe, "--headless=new", "--disable-gpu", "--no-first-run", "--disable-extensions",
             "--allow-file-access-from-files", f"--user-data-dir={profile}",
             *([f"--virtual-time-budget={budget_ms}"] if budget_ms else []), "--dump-dom", url],
            capture_output=True, timeout=timeout,
        )
    return proc.stdout.decode("utf-8", "replace")


def file_url(path):
    return Path(path).resolve().as_uri()


def result_json(dom, element_id="result"):
    """Extract the JSON the test page wrote into <pre id="result">."""
    import html
    import json
    import re

    m = re.search(r'<pre id="%s">(.*?)</pre>' % element_id, dom, re.S)
    if not m:
        raise AssertionError("test page produced no result: " + dom[:400])
    return json.loads(html.unescape(m.group(1)))
