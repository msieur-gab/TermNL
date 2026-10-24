"""python3 -m termnl.server — the thin API and the chat page, on this device.

    GET  /                 the chat page (web/)
    GET  /api/hello        "TermNL is here", for a client looking for it on the network
    GET  /api/settings     the settings panel: show commands, admin mode (switches), name
    POST /api/settings     {"show commands": "on"}, {"name": "Gab"} — written back to settings.md
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
import subprocess
import sys
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import importlib

from . import readers
from .device import Device
from .load import HERE, ROOT, load_language, load_settings
from .runner import run
from .text import fill, pick

WEB = os.path.join(ROOT, "web")
LOGS = os.path.join(ROOT, "logs")
SWITCHES = ("show commands", "admin mode")
WORDS = ("name",)  # settings that hold words, set in the settings panel or by "call me Gab"
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml"}


class TermNL:
    # @doc, what people keep: a sentence goes to the host's documents only when TermNL doesn't understand it,
    # or only guesses with a word it doesn't know; they answer only above these scores. Measured on 23 Oct with
    # the desk's MiniLM, Gab's 85 sentences and the 35 Ask test questions: 24 of 24 questions, none of his commands.
    NOTES = {"no skill": 0.40, "guess": 0.45}

    def __init__(self, root=ROOT, home=None, agent="agent", simulate=(), screen=None, doc=None):
        """simulate, screen and doc are for a host that holds TermNL (Symbiot): the skills (by their `does:`) it
        simulates on top of settings.md's, never fewer; which commands its own screen does (open a file in its
        window), not run here but handed over as "screen"; and its documents, doc(question) → {best, results}."""
        self.root = root
        self.also_simulated = set(simulate)
        self.screen = screen or (lambda command: False)
        self.doc = doc
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
        self.training = None  # learning again: {started, process}, then {done, ok, seconds, error} until it is told
        # how the model is trained again on this device: the lowest priority, two threads, so the board stays usable
        self.trainer = ["nice", "-n", "19", sys.executable, "-m", "termnl.train"]
        self.sessions = {}
        self.lock = threading.Lock()

    def simulated(self, skill_id):
        does = next((s["does"] for s in self.lang["skills"] if s["id"] == skill_id), "")
        return does in self.also_simulated or does in [d.strip() for d in (self.settings.get("simulate") or "").split(",")]

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

    def panel(self):
        """what the settings panel shows: the switches, and the words (the person's name)"""
        return {**{k: self.settings.get(k) or "off" for k in SWITCHES}, **{k: self.settings.get(k) or "" for k in WORDS}}

    def agent(self, session):
        if session not in self.sessions:
            self.sessions[session] = self.Agent(**self.lang, settings=self.settings, device=self.device)
        return self.sessions[session]

    def train(self):
        """"learn what I taught you": trains the model again from the skill files, in the background. The
        model in use is replaced only when the new one is whole (train.py); the one before stays beside it."""
        if self.training and "process" in self.training:
            return False
        env = {**os.environ, "OPENBLAS_NUM_THREADS": "2", "OMP_NUM_THREADS": "2"}
        process = subprocess.Popen(self.trainer, cwd=os.path.dirname(HERE), env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, start_new_session=True)
        self.training = {"started": time.time(), "process": process}
        return True

    def learnt(self):
        """once training is over: the new model is loaded, and the next reply says how it went (a note)"""
        t = self.training
        if not t or "process" not in t or t["process"].poll() is None:
            return None
        out, err = t["process"].communicate()
        seconds = time.time() - t["started"]
        self.training = None
        a = self.Agent(**self.lang, settings=self.settings, device=self.device)
        if t["process"].returncode != 0:
            return a.reply("learning failed", {"error": (err.strip().splitlines() or ["code %d" % t["process"].returncode])[-1]})
        self.lang = load_language("en")
        for session in self.sessions.values():
            session.model = self.lang["model"]
        took = readers.since(seconds, readers.Words(self.lang["lists"]["readings"]))
        return a.reply("learnt", {"time": took})

    def say(self, text, session):
        with self.lock:
            done = self.learnt()
            a = self.agent(session)
            r = a.hear(text)
            r = self.notes(a, r, text) or r
            if r.pop("trains", None) and not self.train():
                r["say"] = a.reply("still learning")
            command = r.pop("command", None)
            for key, value in (r.get("changes") or {}).items():  # "call me Gab", "turn admin mode on"
                self.set(key, value)
            if r["outcome"] == "act" and r.get("reads"):
                self.read(a, r, command)
            elif r["outcome"] == "act" and command:
                label = next(s["label"] for s in self.lang["skills"] if s["id"] == r["skill"])
                if self.simulated(r["skill"]):
                    r["ran"] = "simulated"
                    r["say"] = a.reply("simulated", {"label": label})
                    r["show"] = command  # what would have run, always shown when nothing ran
                elif self.screen(command):
                    r["ran"], r["screen"] = "screen", command  # the host's screen does it
                else:
                    out = self.execute(a, r, command)
                    if out is not None:
                        r["ran"] = "ran"
                        r["say"] = r["say"].replace("{output}", out.strip())
            r["here"] = a.here["label"]
            if done:  # training ended since the last turn: said before the reply
                r["say"] = done + " " + r["say"]
            self.log(session, text, r, command)
            r.pop("teach", None)  # the learning inbox comes next; nothing is learned yet
            r.pop("inbox", None)
            return r

    def notes(self, a, r, text):
        """the host's documents answer instead, when TermNL doesn't understand or only guesses, and they match;
        else None. They are only read: what they hold never becomes a command."""
        floor = self.NOTES["no skill"] if r["outcome"] == "abstain" and r.get("reason") == "no skill" else \
            self.NOTES["guess"] if r["outcome"] == "ask" and r.get("how") == "model" and r.get("unknown") else None
        if floor is None or not self.doc:
            return None
        try:
            found = self.doc(text)
        except Exception:  # the host's documents can't answer: TermNL's own reply stands
            return None
        if not found or (found.get("best") or 0) < floor or not found.get("results"):
            return None
        a.pending = None  # the guess's question is dropped with it
        return {"outcome": "act", "skill": "@doc", "say": a.reply("in your documents"), "ran": "read",
                "documents": found["results"][:5]}

    def execute(self, a, r, command):
        """runs a skill's command → its output, or None when it failed (the reply then says why)"""
        done = run(command, self.device.home)
        self.device.forget()
        if self.settings.get("show commands") == "on":
            r["output"] = (done["out"] + done["err"]).strip()
        if done["code"] != 0:
            error = (done["err"].strip().splitlines() or ["code %d" % done["code"]])[-1]
            r["ran"], r["say"], r["show"] = "failed", a.reply("failed", {"error": error}), command
            return None
        return done["out"]

    def read(self, a, r, command=None):
        """a reading skill: the device reads itself, or the skill's command runs and its output is read
        (Wi-Fi, the network, Bluetooth); the reply is the one written for what was found"""
        skill = next(s for s in self.lang["skills"] if s["id"] == r["skill"])
        try:
            kinds = {k: v["kind"] for k, v in skill["values"].items()}
            args = {k: self.device.path(v) if kinds.get(k) == "@sys.folder" else v for k, v in r.pop("args", {}).items()}
            if command:
                out = self.execute(a, r, command)
                if out is None:
                    r.pop("reads", None)
                    return
                args["output"] = out
            found = readers.read(r.pop("reads"), words=self.lang["lists"]["readings"], **args)
        except (OSError, ValueError, KeyError, IndexError) as e:
            r["ran"], r["say"] = "failed", a.reply("failed", {"error": str(e)})
            return
        lines = skill["when"].get(found["level"])
        said = {k: v for k, v in r.pop("values", {}).items() if k != "output"}
        user = self.settings.get("name") or ""
        r["say"] = fill(pick(lines, random.random, user), {**said, **found["values"], "user": user}) if lines else a.reply("cannot read")
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
                return self.send(app.panel())
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
                        elif k in WORDS and isinstance(v, str):
                            app.set(k, " ".join(v.split())[:40])
                return self.send(app.panel())
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
