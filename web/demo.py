"""The demo: TermNL itself, run in the visitor's browser (Pyodide, from demo.html), on a pretend device.

The server's own turn (server.py) answers each sentence, so the demo says what the board would say. Three things are
pretend: the device (the test device's folders and files, tests/device.py, and made-up readings: temperature,
memory, Wi-Fi…) and every command, shown and never run. Learning is real but stays in the visitor's tab: a skill
taught in the page is read at once, and "learn what I taught you" trains the model again in a background worker
of the page (demo.html), whose model replaces this one when it is whole."""
import json
import os
import re
import socket
import sys
import threading
import time
import types

if not hasattr(socket, "AF_UNIX"):  # a browser has no local sockets; server.py only names it (--socket)
    socket.AF_UNIX = 1

from termnl import readers  # noqa: E402 (after the socket's stand-in)
from termnl.load import load_language, model_path  # noqa: E402
from termnl.server import TermNL  # noqa: E402
from tests.device import LISTS as TEST_LISTS, PretendDevice

IN_BROWSER = sys.platform == "emscripten"
NOTHING = "\x00"  # what a command that didn't run answered
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
# what a few commands would answer, for the replies that quote it ({output}); any other such reply says it only pretends
OUTPUT = {
    "check-kernel": "6.1.31-sun50iw9",
    "check-uptime": "up 3 days, 4 hours",
    "check-service": "active",
    "check-music": "Bonobo – Kong",
    "show-log": "Nov 25 10:02 board systemd[1]: Started nginx.service.\nNov 25 10:02 board nginx[812]: ready",
    "show-remote": "Documents/  Music/  notes.md",
    "ping-remote": "3 packets transmitted, 3 received, 0% packet loss",
    "show-users": "visitor  pts/0  Nov 25 10:02",
}
# the demo's board: the folders most computers have (Gab, 25 Nov: "download, trash, document, pictures, music. So we
# have enough to move around"); the tests keep their own device (tests/device.py)
FOLDERS = [{"value": "$HOME", "names": ["home", "home folder", "my home"]}] + [
    {"value": "$HOME/" + name, "names": [name, name.lower()] + more}
    for name, more in [("Desktop", []), ("Documents", ["docs", "my documents"]), ("Downloads", ["my downloads"]),
                       ("Music", ["my music"]), ("Pictures", ["my pictures"]), ("Videos", ["my videos"])]]
FILES = {
    "$HOME": ["todo.txt", "backup.tar.gz"],
    "$HOME/Desktop": ["shopping.md"],
    "$HOME/Documents": ["note.md", "report.pdf", "groceries.md", "plan.txt"],
    "$HOME/Downloads": ["movie.mkv", "setup.sh", "photos.tar.gz", "manual.pdf"],
    "$HOME/Music": ["Kong.mp3", "Kerala.mp3", "Cirrus.mp3"],
    "$HOME/Pictures": ["beach.jpg", "bike.png", "garden.jpg"],
    "$HOME/Videos": ["holiday.mp4", "birthday.mov"],
}
TRASH = ["old-notes.md", "draft.txt"]
LISTS = {**TEST_LISTS, "folder": FOLDERS, "music": [  # artists, albums and titles, as read from ~/Music
    {"value": "Bonobo", "names": ["Bonobo"]},
    {"value": "Migration", "names": ["Migration"]},
    {"value": "Black Sands", "names": ["Black Sands"]},
    {"value": "Kong", "names": ["Kong"]},
    {"value": "Kerala", "names": ["Kerala"]},
    {"value": "Cirrus", "names": ["Cirrus"]},
]}
SIZES = {"report.pdf": 240, "manual.pdf": 380, "movie.mkv": 2400, "photos.tar.gz": 1800, "backup.tar.gz": 900, "setup.sh": 6,
         "Kong.mp3": 900, "Kerala.mp3": 950, "Cirrus.mp3": 880, "beach.jpg": 420, "bike.png": 310, "garden.jpg": 390,
         "holiday.mp4": 2100, "birthday.mov": 1600}  # in KB, small enough for a browser tab


def pretend_board():
    """the board's own files, written where the readers look for them; the rest of what they ask is answered here"""
    if IN_BROWSER:
        for path, text in BOARD.items():
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(text)
        readers.os.statvfs = lambda where: types.SimpleNamespace(f_blocks=7_500_000, f_bavail=4_620_000, f_frsize=4096)
        readers.os.cpu_count = lambda: 4
        usb = "/sys/bus/usb/devices"  # what is plugged in: a USB stick and a Meshtastic radio (as in tests/test_readers.py)
        for name, vendor, maker, product, cls, (c, inside) in [
                ("usb1", "1d6b", "Linux", "EHCI", "09", ("09", "")),
                ("1-1", "0781", "SanDisk", "Ultra", "00", ("08", "host0/target0:0:0/0:0:0:0/block/sda")),
                ("1-2", "239a", "Seeed Studio", "XIAO nRF52840", "ef", ("02", "tty/ttyACM0"))]:
            d = os.path.join(usb, name)
            for k, v in dict(idVendor=vendor, idProduct="0001", manufacturer=maker, product=product, bDeviceClass=cls).items():
                os.makedirs(d, exist_ok=True)
                with open(os.path.join(d, k), "w") as f:
                    f.write(v + "\n")
            os.makedirs(os.path.join(d, name + ":1.0", inside), exist_ok=True)
            with open(os.path.join(d, name + ":1.0", "bInterfaceClass"), "w") as f:
                f.write(c + "\n")
            if inside.endswith("sda"):
                with open(os.path.join(d, name + ":1.0", inside, "size"), "w") as f:
                    f.write("62521344\n")
        readers.platform = types.SimpleNamespace(release=lambda: "6.1.31-sun50iw9", node=lambda: "orangepi",
                                                 machine=lambda: "aarch64")
    readers.subprocess = types.SimpleNamespace(run=lambda *a, **k: types.SimpleNamespace(stdout=PS, stderr="", returncode=0))
    for folder, files in FILES.items():  # the test device's tree, so listing a folder lists it
        where = folder.replace("$HOME", HOME)
        os.makedirs(where, exist_ok=True)
        for name in files:
            with open(os.path.join(where, name), "wb") as f:
                f.write(b"\0" * 1024 * SIZES.get(name, 3))
    trash = os.path.join(HOME, ".local", "share", "Trash")
    for part in ("files", "info"):
        os.makedirs(os.path.join(trash, part), exist_ok=True)
    for name in TRASH:
        with open(os.path.join(trash, "files", name), "wb") as f:
            f.write(b"\0" * 2048)
        with open(os.path.join(trash, "info", name + ".trashinfo"), "w") as f:
            f.write("[Trash Info]\nPath=%s/Documents/%s\nDeletionDate=2026-11-20T18:04:00\n" % (HOME, name))


class Device(PretendDevice):
    """the demo's board, as the test device answers, with what the server asks of a real one"""
    home = HOME
    own = {}
    wifi = ""

    def list(self, kind):
        return LISTS.get(kind, [])

    def files(self, folder):
        return FILES.get(folder, [])

    def exists(self, path):
        folder, _, name = path.rpartition("/")
        return path in [d["value"] for d in FOLDERS] or name in FILES.get(folder, [])

    def find(self, test):
        return [{"folder": folder, "file": f, "label": next(d for d in FOLDERS if d["value"] == folder)["names"][0]}
                for folder, files in FILES.items() for f in files if test(f)]

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
        self.inbox = []
        self.taught = []  # the skill folders taught in this tab  # what TermNL didn't understand, and the guesses a yes confirmed (to teach), in this visit

    def simulated(self, skill_id):
        """nothing is simulated the board's way ("I only pretend to…"): each skill answers with its own reply, as on
        the board, your name in it, and the command is marked as not run (_say)"""
        return False

    def _say(self, text, session, screen):
        self.ran = None
        r = super()._say(text, session, screen)
        if self.ran and r.get("ran") == "ran":
            r["ran"], r["show"] = "simulated", self.ran
            if NOTHING in r["say"]:  # a reply that would quote what the command said, which nobody knows here
                label = next(s["label"] for s in self.lang["skills"] if s["id"] == r["skill"])
                r["say"] = self.agent(session).reply("simulated", {"label": label})
            elif r["skill"] in OUTPUT:
                r["made up"] = True
        return r

    def set(self, key, value):  # kept for this visit only
        self.settings[key] = value

    def log(self, session, text, r, command=None):
        """the board writes every turn to logs/; here, only what the inbox shows"""
        if r.get("inbox"):
            self.inbox.append({"text": r["inbox"], "reason": r.get("reason") or "not understood"})
        if r.get("teach"):
            self.inbox.append({"text": r["teach"]["text"], "teach": r["teach"]["skill"]})

    def read(self, a, r, command=None):
        """as on the board; the command a reader runs is shown, since nothing ran, and what was read is given whole
        (r["reading"]: its kind, level and values), so the page can draw it: a gauge, a list of files"""
        kind, found, plain = r.get("reads"), {}, readers.read

        def kept(name, **args):
            found.update(plain(name, **args))
            return found

        readers.read = kept
        try:
            super().read(a, r, command)
        finally:
            readers.read = plain
        if command:
            r["show"] = command
        if found:
            r["reading"] = {"kind": kind, "level": found.get("level"), "values": found.get("values", {})}

    def execute(self, a, r, command, given=None):
        """nothing runs: a reader's command (Wi-Fi, the network) says what it would have said; another command is kept
        to be shown, with what it would have answered when that is known (OUTPUT), else a mark that nothing ran"""
        skill = next((s for s in self.lang["skills"] if s["id"] == r.get("skill")), {})
        if skill.get("reads"):
            return SAID.get(skill["reads"], "")
        self.ran = command
        if r.get("skill") == "find-file":  # find answers with the paths of what it found on the board
            said = re.search(r"-iname '?\*?([^*']+)", command)
            found = [f"{folder.replace('$HOME', HOME)}/{f}" for folder, files in FILES.items() for f in files
                     if said and said.group(1).lower() in f.lower()]
            return "\n".join(found) or NOTHING
        return OUTPUT.get(r.get("skill"), NOTHING)

    def train(self, session):
        """"learn what I taught you": the page trains the model again in a worker, from the skill files as they are
        in this tab (its taught skills among them); the chat goes on meanwhile, as on the board"""
        if self.training:
            return False
        import js  # the page (demo.html)
        skills = os.path.join(os.path.dirname(readers.__file__), "languages", "en", "skills")
        taught = {d: open(os.path.join(skills, d, "skill.md"), encoding="utf-8").read() for d in self.taught}
        js.termnlTrain(json.dumps(taught))
        self.training = {"started": time.time(), "session": session}
        return True

    def learnt(self):
        """server.py asks at each turn whether training has ended; here the worker says so itself (trained)"""

    def trained(self, model=None, error=None):
        """the worker is done: its model replaces the one in use, and the conversation that asked is told"""
        t, self.training = self.training, None
        if not t:
            return
        if model:
            with open(model_path("en"), "w", encoding="utf-8") as f:
                f.write(model)
            self.relearn()
        a = self.agent(t["session"])
        took = readers.since(time.time() - t["started"], readers.Words(self.lang["lists"]["readings"]))
        self.told[t["session"]] = a.reply("learnt", {"time": took}) if model else a.reply("learning failed", {"error": error or ""})

    def learning(self, session):
        return {"learning": self.training is not None, "say": self.told.pop(session, None)}

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
    if path == "/api/board":  # the pretend board, for the page to show: its lists, and the files in each folder
        return json.dumps({"skills": len(demo.lang["skills"]),
                           "lists": {kind: [d["names"][0] for d in items] for kind, items in LISTS.items()},
                           "files": [{"folder": next(d["names"][0] for d in FOLDERS if d["value"] == folder), "files": files}
                                     for folder, files in FILES.items()]})
    if path == "/api/inbox":
        return json.dumps(demo.inbox)
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
        elif body["id"] not in demo.taught:
            demo.taught.append(body["id"])
        return json.dumps({"errors": errors, "skills": len(demo.lang["skills"])})
    return json.dumps({"error": "not here: " + path})
