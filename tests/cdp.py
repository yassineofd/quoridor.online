"""Minimal Chrome DevTools Protocol driver (standard library only) for UI tests.

Launches headless Edge/Chrome with a throwaway profile and lets a test navigate, evaluate
JavaScript, click, type and take screenshots. Not a general automation library.
"""

import base64
import json
import os
import socket
import struct
import subprocess
import tempfile
import time
import urllib.request

from tests import browser as _browser


class WebSocket:
    def __init__(self, host, port, path):
        self.sock = socket.create_connection((host, port), timeout=60)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall(
            (f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
             f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode()
        )
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("websocket handshake failed")
            buf += chunk
        self.buf = buf.split(b"\r\n\r\n", 1)[1]

    def _read(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(1 << 16)
            if not chunk:
                raise ConnectionError("websocket closed")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def send(self, text):
        data = text.encode()
        header = bytearray([0x81])
        n = len(data)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            header += bytes([0x80 | 127]) + struct.pack(">Q", n)
        mask = os.urandom(4)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.sock.sendall(bytes(header) + mask + masked)

    def recv(self):
        message = b""
        while True:
            b1, b2 = self._read(2)
            fin, opcode, length = b1 & 0x80, b1 & 0x0F, b2 & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._read(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._read(8))[0]
            payload = self._read(length)
            if opcode == 0x9:  # ping
                self.sock.sendall(bytes([0x8A, 0x80]) + os.urandom(4))
                continue
            if opcode == 0x8:
                raise ConnectionError("websocket closed by browser")
            message += payload
            if fin:
                return message.decode("utf-8", "replace")


class Page:
    def __init__(self, port=9333, width=1280, height=900, mobile=False, touch=False):
        exe = _browser.find_browser()
        if not exe:
            raise FileNotFoundError("no Edge/Chrome found")
        self.profile = tempfile.TemporaryDirectory()
        self.proc = subprocess.Popen(
            [exe, "--headless=new", "--disable-gpu", "--no-first-run", "--disable-extensions",
             "--no-default-browser-check", f"--remote-debugging-port={port}", f"--user-data-dir={self.profile.name}",
             "--remote-allow-origins=*", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        target = None
        for _ in range(100):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2) as r:
                    pages = [t for t in json.loads(r.read()) if t.get("type") == "page"]
                if pages:
                    target = pages[0]
                    break
            except Exception:
                pass
            time.sleep(0.2)
        if not target:
            self.close()
            raise RuntimeError("browser did not start")
        path = "/" + target["webSocketDebuggerUrl"].split("/", 3)[3]
        self.ws = WebSocket("127.0.0.1", port, path)
        self._id = 0
        self.events = []
        self.console = []
        self.send("Page.enable")
        self.send("Runtime.enable")
        self.set_viewport(width, height, mobile, touch)

    # ---- protocol -------------------------------------------------------------------
    def send(self, method, **params):
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
            self._event(msg)

    def _event(self, msg):
        if msg.get("method") == "Runtime.consoleAPICalled":
            args = [a.get("value", a.get("description", "")) for a in msg["params"]["args"]]
            self.console.append((msg["params"]["type"], " ".join(str(a) for a in args)))
        elif msg.get("method") == "Runtime.exceptionThrown":
            d = msg["params"]["exceptionDetails"]
            self.console.append(("exception", d.get("exception", {}).get("description") or d.get("text", "")))
        self.events.append(msg)

    def pump(self, seconds):
        """Read events for a while (lets timers, fetches and workers run)."""
        end = time.time() + seconds
        self.ws.sock.settimeout(0.1)
        try:
            while time.time() < end:
                try:
                    self._event(json.loads(self.ws.recv()))
                except socket.timeout:
                    pass
        finally:
            self.ws.sock.settimeout(60)

    def set_viewport(self, width, height, mobile=False, touch=False):
        self.send("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1, mobile=mobile)
        self.send("Emulation.setTouchEmulationEnabled", enabled=touch)
        self.touch = touch

    def goto(self, url, wait=0.6):
        self.send("Page.navigate", url=url)
        for _ in range(100):
            if self.js("document.readyState") == "complete":
                break
            time.sleep(0.1)
        self.pump(wait)

    def js(self, expr):
        res = self.send("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in res:
            d = res["exceptionDetails"]
            raise RuntimeError("js error: " + (d.get("exception", {}).get("description") or d.get("text", "")) + " in " + expr[:120])
        return res["result"].get("value")

    def wait_for(self, expr, timeout=10, step=0.1):
        end = time.time() + timeout
        while time.time() < end:
            try:
                v = self.js("!!(" + expr + ")")  # DOM nodes can't be returned by value
            except RuntimeError:
                v = None
            if v:
                return v
            self.pump(step)
        raise AssertionError("timed out waiting for: " + expr)

    # ---- input ----------------------------------------------------------------------
    def center(self, selector):
        r = self.js(f"(function(){{var e=document.querySelector({json.dumps(selector)});if(!e)return null;e.scrollIntoView({{block:'center'}});var b=e.getBoundingClientRect();return [b.left+b.width/2,b.top+b.height/2,b.width,b.height];}})()")
        if not r:
            raise AssertionError("no element " + selector)
        return r

    def click_at(self, x, y):
        if self.touch:
            self.send("Input.dispatchTouchEvent", type="touchStart", touchPoints=[{"x": x, "y": y}])
            self.send("Input.dispatchTouchEvent", type="touchEnd", touchPoints=[])
        else:
            self.send("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y)
            self.send("Input.dispatchMouseEvent", type="mousePressed", x=x, y=y, button="left", clickCount=1)
            self.send("Input.dispatchMouseEvent", type="mouseReleased", x=x, y=y, button="left", clickCount=1)
        self.pump(0.15)

    def move_to(self, x, y):
        self.send("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y)
        self.pump(0.05)

    def click(self, selector):
        x, y, _, _ = self.center(selector)
        self.click_at(x, y)

    def type_text(self, selector, text):
        self.js(f"document.querySelector({json.dumps(selector)}).focus()")
        self.send("Input.insertText", text=text)
        self.pump(0.05)

    def key(self, key, code=None):
        codes = {"Enter": 13, "Escape": 27, "ArrowLeft": 37, "ArrowUp": 38, "ArrowRight": 39, "ArrowDown": 40, " ": 32}
        vk = codes.get(key, ord(key.upper()) if len(key) == 1 else 0)
        text = key if len(key) == 1 else ("\r" if key == "Enter" else "")
        self.send("Input.dispatchKeyEvent", type="keyDown", key=key, code=code or key, windowsVirtualKeyCode=vk, text=text)
        self.send("Input.dispatchKeyEvent", type="keyUp", key=key, code=code or key, windowsVirtualKeyCode=vk)
        self.pump(0.1)

    def screenshot(self, path):
        data = self.send("Page.captureScreenshot", format="png")["data"]
        with open(path, "wb") as f:
            f.write(base64.b64decode(data))

    def close(self):
        try:
            self.proc.terminate()
            self.proc.wait(10)
        except Exception:
            self.proc.kill()
        try:
            self.profile.cleanup()
        except Exception:
            pass
