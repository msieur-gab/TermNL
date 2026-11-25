"""The demo: TermNL itself, run in the visitor's browser (Pyodide, from demo.html), on a pretend device.

The server's own turn (server.py) answers each sentence, so the demo says what the board would say. Three things are
pretend: the device (the test device's folders and files, tests/device.py, and made-up readings: temperature,
memory, Wi-Fi…); every command, shown and never run; and learning, which loads the skill files again without
training the model (a skill taught in the page knows the sentences written in it)."""
import json
import os
import socket
import sys
import threading
import time
import types

if not hasattr(socket, "AF_UNIX"):  # a browser has no local sockets; server.py only names it (--socket)
    socket.AF_UNIX = 1

from termnl import readers  # noqa: E402 (after the socket's stand-in)
from termnl.load import load_language  # noqa: E402
from termnl.server import TermNL  # noqa: E402
from tests.device import FILES, FOLDERS, PretendDevice

IN_BROWSER = sys.platform == "emscripten"
HOME = "/home/visitor" if IN_BROWSER else os.path.join(os.environ.get("TMPDIR", "/tmp"), "termnl-demo-home")

# what the board would read from itself: an Orange Pi Zero 2W, as on Gab's desk
BOARD = {
    "/proc/meminfo": "MemTotal:        1512340 kB\nMemFree:          402112 kB\nMemAvailable:     941268 kB\n",
    "/proc/uptime": "273641.52 1012345.10\n",
    "/proc/mounts": "/dev/mmcblk0p1 / ext4 rw,noatime 0 0\nproc /proc proc rw 0 0\n",
    "/proc/device-tree/model": "Orange Pi Zero 2W\x00",
    "/proc/cpuinfo": "processor\t: 0\nmodel name\t: ARMv8 Processor rev 4 (v8l)\nHardware\t: sun50iw9\n",
    "/etc/os-release": 'PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"\nNAME="Debian GNU/Linux"\n',
    "/sys/class/thermal/thermal_zone0/type": "cpu-thermal\n",
    "/sys/class/thermal/thermal_zone0/temp": "47312\n",
}
PS = "firefox-esr 284512 12.0\nfirefox-esr 120344 3.1\nmpd 22180 0.4\nsshd 8120 0.0\npython3 31544 1.2\n"
# what the commands of the readers that run one say (as in tests/test_readers.py)
SAID = {
    "wifi": "Connected to 02:00:5e:10:00:01 (on wlan0)\n\tSSID: Garden Network\n\tfreq: 5180.0\n\tsignal: -52 dBm\n"
            "BSS 02:00:5e:10:00:01(on wlan0) -- associated\n\tsignal: -52.00 dBm\n\tSSID: Garden Network\n"
            "BSS 11:22:33:44:55:01(on wlan0)\n\tsignal: -61.00 dBm\n\tSSID: Wonderland\n"
            "BSS 11:22:33:44:55:03(on wlan0)\n\tsignal: -78.00 dBm\n\tSSID: Caf\\xc3\\xa9\n",
    "network": "lo               UNKNOWN        127.0.0.1/8 \nwlan0            UP             192.168.1.51/24 \n",
    "bluetooth": "Controller 02:00:5e:10:00:aa (public)\n\tName: orangepi\n\tAlias: orangepi\n\tPowered: yes\n",
}
SAID["networks"] = SAID["wifi"]


def pretend_board():
    """the board's own files, written where the readers look for them; the rest of what they ask is answered here"""
    if IN_BROWSER:
        for path, text in BOARD.items():
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(text)
        readers.os.statvfs = lambda where: types.SimpleNamespace(f_blocks=7_500_000, f_bavail=4_620_000, f_frsize=4096)
        readers.os.cpu_count = lambda: 4
        readers.platform = types.SimpleNamespace(release=lambda: "6.1.31-sun50iw9", node=lambda: "orangepi",
                                                 machine=lambda: "aarch64")
    readers.subprocess = types.SimpleNamespace(run=lambda *a, **k: types.SimpleNamespace(stdout=PS, stderr="", returncode=0))
    for folder, files in FILES.items():  # the test device's tree, so listing a folder lists it
        where = folder.replace("$HOME", HOME)
        os.makedirs(where, exist_ok=True)
        for name in files:
            with open(os.path.join(where, name), "w") as f:
                f.write("")


class Device(PretendDevice):
    """the test device, with what the server asks of a real one"""
    home = HOME
    own = {}
    wifi = ""

    def path(self, value):
        return value.replace("$HOME", HOME)

    def forget(self):
        pass

    def quiet(self):
        pass

    def hear(self, output):
        pass

    def networks(self):
        pass


class Demo(TermNL):
    """the server's turn, with nothing run: every command is shown as what it would have done"""

    def __init__(self):
        self.root, self.also_simulated, self.doc, self.commands = None, set(), None, {}
        self.screen = lambda command: False
        self.version, self.Agent = "agent", __import__("termnl.agent", fromlist=["Agent"]).Agent
        self.lang = load_language("en")
        self.settings = {"show commands": "on", "admin mode": "on", "name": ""}
        self.device = Device()
        self.training, self.told, self.sessions, self.lock = None, {}, {}, threading.Lock()

    def simulated(self, skill_id):
        return True

    def set(self, key, value):  # kept for this visit only
        self.settings[key] = value

    def log(self, *_):
        pass

    def execute(self, a, r, command, given=None):
        """only a reader's command gets here (a reading skill), and what it would have said is made up"""
        return SAID.get(next((s["reads"] for s in self.lang["skills"] if s["id"] == r.get("skill")), ""), "")

    def train(self, session):
        """"learn what I taught you": the skill files are read again, the model stays as trained on the board"""
        started = time.time()
        self.relearn()
        a = self.agent(session)
        self.told[session] = a.reply("learnt", {"time": readers.since(time.time() - started, readers.Words(self.lang["lists"]["readings"]))})
        return True

    def learning(self, session):
        return {"learning": False, "say": self.told.pop(session, None)}

    def relearn(self):
        """the skill files again, a skill taught in the page among them; each conversation starts with them anew"""
        self.lang = load_language("en")
        self.sessions = {}
        return self.lang["errors"]

    def reset(self, session):
        self.sessions.pop(session, None)


pretend_board()
demo = Demo()


def api(method, path, body):
    """what termnl-chat.js and demo.html ask, answered here as server.py's handler would → JSON"""
    body = json.loads(body or "{}")
    path, _, query = path.partition("?")
    session = body.get("session") or dict(p.split("=", 1) for p in query.split("&") if "=" in p).get("session") or "visitor"
    if path == "/api/say":
        return json.dumps(demo.say(body.get("text", ""), session))
    if path == "/api/reset":
        demo.reset(session)
        return json.dumps({"ok": True})
    if path == "/api/learning":
        return json.dumps(demo.learning(session))
    if path == "/api/settings":
        for k, v in body.items():
            if k != "session":
                demo.set(k, v)
        return json.dumps(demo.panel())
    if path == "/api/board":  # the pretend board's folders and files, for the page to show
        return json.dumps([{"folder": next(d["names"][0] for d in FOLDERS if d["value"] == folder), "files": files}
                           for folder, files in FILES.items()])
    if path == "/api/teach":  # a skill written in the page, dropped in as a folder; one that doesn't read is taken out
        if not IN_BROWSER:  # the skill files on a computer are the person's own
            return json.dumps({"errors": ["only in the browser"]})
        folder = os.path.join(os.path.dirname(readers.__file__), "languages", "en", "skills", body["id"])
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "skill.md"), "w", encoding="utf-8") as f:
            f.write(body["text"])
        errors = demo.relearn()
        if errors:
            os.remove(os.path.join(folder, "skill.md"))
            os.rmdir(folder)
            demo.relearn()
        return json.dumps({"errors": errors, "skills": len(demo.lang["skills"])})
    return json.dumps({"error": "not here: " + path})
