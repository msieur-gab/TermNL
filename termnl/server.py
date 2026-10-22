"""python3 -m termnl.server — the thin API and the chat page, on this device.

    GET  /                 the chat page (web/)
    GET  /api/hello        "TermNL is here", for a client looking for it on the network
    GET  /api/settings     the switches: show commands, admin mode
    POST /api/settings     {"show commands": "on"} — written back to settings.md
    POST /api/say          {"text": "...", "session": "..."} → the reply
    POST /api/reset        {"session": "..."} — a new conversation

The API takes sentences and gives replies: never a command. The commands are the skills' own,
filled in by the agent and run here (runner.py), or simulated (settings.md, "simulate:").
No sign-in yet: by default it answers this machine only (--host)."""
import argparse
import json
import os
import re
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .agent import Agent
from .device import Device
from .load import ROOT, load_language, load_settings
from .runner import run

WEB = os.path.join(ROOT, "web")
SWITCHES = ("show commands", "admin mode")
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml"}


class TermNL:
    def __init__(self, root=ROOT, home=None):
        self.root = root
        self.lang = load_language("en", root)
        if self.lang["errors"]:
            raise SystemExit("\n".join(self.lang["errors"]))
        self.settings = load_settings(root)
        self.device = Device(home or self.settings.get("home") or "~/TermNL-home")
        os.makedirs(self.device.home, exist_ok=True)
        self.sessions = {}
        self.lock = threading.Lock()

    def simulated(self, skill_id):
        does = next((s["does"] for s in self.lang["skills"] if s["id"] == skill_id), "")
        return does in [d.strip() for d in (self.settings.get("simulate") or "").split(",")]

    def set(self, key, value):
        """a switch, kept in memory and written back to its line in settings.md"""
        self.settings[key] = value
        path = os.path.join(self.root, "settings.md")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        line = "%s: %s" % (key, value)
        pattern = re.compile(r"^%s:.*$" % re.escape(key), re.M | re.I)
        text = pattern.sub(line, text, count=1) if pattern.search(text) else text.rstrip("\n") + "\n" + line + "\n"
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def agent(self, session):
        if session not in self.sessions:
            self.sessions[session] = Agent(**self.lang, settings=self.settings, device=self.device)
        return self.sessions[session]

    def say(self, text, session):
        with self.lock:
            a = self.agent(session)
            r = a.hear(text)
            command = r.pop("command", None)
            if r["outcome"] == "act" and command:
                label = next(s["label"] for s in self.lang["skills"] if s["id"] == r["skill"])
                if self.simulated(r["skill"]):
                    r["ran"] = "simulated"
                    r["say"] = a.reply("simulated", {"label": label})
                    r["show"] = command  # what would have run, always shown when nothing ran
                else:
                    done = run(command, self.device.home)
                    self.device.forget()
                    if done["code"] == 0:
                        r["ran"] = "ran"
                        r["say"] = r["say"].replace("{output}", done["out"].strip())
                    else:
                        r["ran"] = "failed"
                        error = (done["err"].strip().splitlines() or ["code %d" % done["code"]])[-1]
                        r["say"] = a.reply("failed", {"error": error})
                        r["show"] = command
                    if self.settings.get("show commands") == "on":
                        r["output"] = (done["out"] + done["err"]).strip()
            r["here"] = a.here["label"]
            r.pop("teach", None)  # the learning inbox comes next; nothing is learned yet
            r.pop("inbox", None)
            return r


def handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def send(self, body, kind="application/json", code=200):
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def body(self):
            n = int(self.headers.get("Content-Length") or 0)
            try:
                return json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return {}

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/api/hello":
                return self.send({"termnl": True, "host": socket.gethostname()})
            if path == "/api/settings":
                return self.send({k: app.settings.get(k) or "off" for k in SWITCHES})
            f = os.path.normpath(os.path.join(WEB, "index.html" if path == "/" else path.lstrip("/")))
            if not f.startswith(WEB + os.sep) or not os.path.isfile(f):
                return self.send({"error": "not found"}, code=404)
            with open(f, "rb") as fh:
                self.send(fh.read(), TYPES.get(os.path.splitext(f)[1], "application/octet-stream"))

        def do_POST(self):
            path, b = self.path.split("?")[0], self.body()
            if path == "/api/say":
                text = str(b.get("text") or "")[:500]
                return self.send(app.say(text, str(b.get("session") or "default")))
            if path == "/api/reset":
                with app.lock:
                    app.sessions.pop(str(b.get("session") or "default"), None)
                return self.send({"ok": True})
            if path == "/api/settings":
                with app.lock:
                    for k, v in b.items():
                        if k in SWITCHES and v in ("on", "off"):
                            app.set(k, v)
                return self.send({k: app.settings.get(k) or "off" for k in SWITCHES})
            return self.send({"error": "not found"}, code=404)
    return Handler


def main():
    p = argparse.ArgumentParser(description="TermNL: talk to this machine in plain words.")
    p.add_argument("--host", default="127.0.0.1", help="address to answer on (default: this machine only)")
    p.add_argument("--port", type=int, default=8810)
    p.add_argument("--home", help="the folder home means, instead of settings.md's (for trying things out)")
    a = p.parse_args()
    app = TermNL(home=a.home)
    print("TermNL on http://%s:%d — home: %s" % (a.host, a.port, app.device.home))
    ThreadingHTTPServer((a.host, a.port), handler(app)).serve_forever()


if __name__ == "__main__":
    main()
