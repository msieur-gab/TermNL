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
import datetime
import json
import os
import random
import re
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import importlib

from . import readers
from .device import Device
from .load import ROOT, load_language, load_settings
from .runner import run
from .text import fill

WEB = os.path.join(ROOT, "web")
LOGS = os.path.join(ROOT, "logs")
SWITCHES = ("show commands", "admin mode")
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml"}


class TermNL:
    def __init__(self, root=ROOT, home=None, agent="agent"):
        self.root = root
        # agent: agent.py; back: back_agent.py, the version before it, kept for comparison
        self.version = agent
        self.Agent = importlib.import_module(".agent" if agent == "agent" else ".back_agent", __package__).Agent
        self.lang = load_language("en")
        if self.lang["errors"]:
            raise SystemExit("\n".join(self.lang["errors"]))
        self.settings = load_settings(root)
        self.device = Device(home or self.settings.get("home") or "~/TermNL-home",
                             home_names=[" ".join(p) for p in self.lang["lists"]["conversation"].get("home folder", [["home"]])])
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
            self.sessions[session] = self.Agent(**self.lang, settings=self.settings, device=self.device)
        return self.sessions[session]

    def say(self, text, session):
        with self.lock:
            a = self.agent(session)
            r = a.hear(text)
            command = r.pop("command", None)
            if r["outcome"] == "act" and r.get("reads"):
                self.read(a, r)
            elif r["outcome"] == "act" and command:
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
            self.log(session, text, r, command)
            r.pop("teach", None)  # the learning inbox comes next; nothing is learned yet
            r.pop("inbox", None)
            return r

    def read(self, a, r):
        """a reading skill: the device reads itself, and the reply is the one written for what it found"""
        skill = next(s for s in self.lang["skills"] if s["id"] == r["skill"])
        try:
            kinds = {k: v["kind"] for k, v in skill["values"].items()}
            args = {k: self.device.path(v) if kinds.get(k) == "@sys.folder" else v for k, v in r.pop("args", {}).items()}
            found = readers.read(r.pop("reads"), **args)
        except (OSError, ValueError, KeyError, IndexError) as e:
            r["ran"], r["say"] = "failed", a.reply("failed", {"error": str(e)})
            return
        lines = skill["when"].get(found["level"])
        said = {k: v for k, v in r.pop("values", {}).items() if k != "output"}
        r["say"] = fill(random.choice(lines), {**said, **found["values"], "user": self.settings.get("name") or ""}) if lines else a.reply("cannot read")
        if r.get("note"):
            r["say"] = r["note"] + " " + r["say"]
        r["ran"], r["level"] = "read", found["level"]
        if found.get("table"):
            r["table"] = found["table"]

    def log(self, session, text, r, command=None):
        """every turn, one line of JSON in logs/<date>.jsonl: the real sentences people type"""
        os.makedirs(LOGS, exist_ok=True)
        now = datetime.datetime.now()
        line = {"at": now.isoformat(timespec="seconds"), "session": session[:8], "agent": self.version, "text": text,
                **{k: r[k] for k in ("outcome", "skill", "how", "p", "unknown", "say", "ran", "level", "show", "teach", "inbox", "reason") if r.get(k) is not None},
                **({"command": command} if command else {})}
        with open(os.path.join(LOGS, now.strftime("%Y-%m-%d") + ".jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")


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
    p.add_argument("--agent", default="agent", choices=["agent", "back"], help="which dialogue: agent.py, or back_agent.py (the version before)")
    a = p.parse_args()
    app = TermNL(home=a.home, agent=a.agent)
    print("TermNL (agent %s) on http://%s:%d — home: %s" % (a.agent, a.host, a.port, app.device.home))
    ThreadingHTTPServer((a.host, a.port), handler(app)).serve_forever()


if __name__ == "__main__":
    main()
