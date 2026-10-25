"""The device as the agent sees it: the values it can list itself (@sys.folder, @sys.service,
@sys.app, @sys.network, @sys.music from ~/Music, @sys.host from ~/.ssh/config) and the files in a folder, all read from this machine.

Folders and files are those under TermNL's home (settings.md, "home:"), the folder that $HOME means
in every command. Hidden folders are skipped. Lists are read again after a few seconds, so a folder
made a moment ago is already known."""
import configparser
import glob
import os
import re
import subprocess
import threading
import time

from .readers import _wifi_list
from .runner import path


def _run(args, timeout=5):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout, env={**os.environ, "PATH": path()}).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


class Device:
    def __init__(self, home, fresh=3, home_names=("home",)):
        self.home = os.path.abspath(os.path.expanduser(home))
        self.home_names = list(home_names)  # what people call it (conversation.md, "home folder")
        self.fresh = fresh
        self._cache = {}
        self.wifi = "termnl-wifi scan"  # how the networks around are heard: show wifi's command, or the one a host lends
        self._heard = (0, [])  # the networks around as last heard, and when
        self._hearing = None

    def path(self, value):
        """$HOME/Documents → the real path"""
        return self.home + value[5:] if value.startswith("$HOME") else value

    def _folders(self, depth=4):
        out = [{"value": "$HOME", "names": self.home_names}]
        for root, dirs, _ in os.walk(self.home):
            dirs[:] = sorted(d for d in dirs if not d.startswith("."))
            if root[len(self.home):].count(os.sep) >= depth:
                dirs[:] = []
            for d in dirs:
                rel = os.path.relpath(os.path.join(root, d), self.home)
                names = [d] + ([d.lower()] if d.lower() != d else [])
                out.append({"value": "$HOME/" + rel, "names": names})
        return out

    def _services(self):
        out = []
        for line in _run(["systemctl", "list-units", "--type=service", "--all", "--no-legend", "--plain"]).splitlines():
            unit = line.split()[0] if line.split() else ""
            if unit.endswith(".service") and "@" not in unit:
                out.append({"value": unit[:-8], "names": [unit[:-8]]})
        return out

    def _apps(self):
        out, seen = [], set()
        for f in sorted(glob.glob("/usr/share/applications/*.desktop") + glob.glob(os.path.expanduser("~/.local/share/applications/*.desktop"))):
            c = configparser.ConfigParser(interpolation=None, strict=False)
            try:
                c.read(f, encoding="utf-8")
                e = c["Desktop Entry"]
            except (configparser.Error, KeyError, UnicodeDecodeError):
                continue
            if e.get("NoDisplay", "").lower() == "true" or e.get("Type", "Application") != "Application":
                continue
            # the program itself: "env VAR=1 prog %u" → prog
            words = [w for w in (e.get("Exec") or "").split() if w != "env" and "=" not in w]
            exe = os.path.basename(words[0]) if words else ""
            name = (e.get("Name") or "").strip()
            if not exe or not name or name.lower() in seen:
                continue
            seen.add(name.lower())
            out.append({"value": exe, "names": [name] + ([exe] if exe.lower() != name.lower() else [])})
        return out

    def _running(self):
        """the installed apps that are running now, each by its process name (what pkill -x matches)"""
        procs = []
        for line in _run(["ps", "-u", str(os.getuid()), "-o", "comm=,args="]).splitlines():
            parts = line.split(None, 1)
            if len(parts) == 2:
                procs.append((parts[0], os.path.basename(parts[1].split()[0])))
        by = {}
        for app in self._apps():
            exe = app["value"]
            # brave-browser-stable starts brave; gnome-terminal runs as gnome-terminal-server
            for comm, prog in procs:
                if prog == exe or exe.startswith(prog + "-") or prog == exe + "-server":
                    by.setdefault(comm, []).append(app)
                    break
        out = []
        for comm, apps in by.items():
            names = []
            # the name that says the program's own name first: "Brave Web Browser", not a web app it runs
            for a in sorted(apps, key=lambda a: comm.split("-")[0].lower() not in a["names"][0].lower()):
                names += [n for n in a["names"] if n not in names]
            out.append({"value": comm, "names": names + ([comm] if comm not in names else [])})
        return out

    AUDIO = (".mp3", ".flac", ".ogg", ".opus", ".m4a", ".wav", ".aac")

    def _music(self):
        """the music in home's Music folder, named as people say it: its artists (the folders), albums (the folders
        in them) and titles (the files, without their track number). "&" can also be said "and"."""
        names = []
        for folder, dirs, files in os.walk(os.path.join(self.home, "Music")):
            dirs[:] = sorted(d for d in dirs if not d.startswith("."))
            names += [d for d in dirs]
            names += [re.sub(r"^\d+\s*[-.]\s*", "", os.path.splitext(f)[0]) for f in sorted(files) if f.lower().endswith(self.AUDIO)]
        out, seen = [], set()
        for n in names:
            if n and n.lower() not in seen:
                seen.add(n.lower())
                out.append({"value": n, "names": [n] + ([n.replace("&", "and")] if "&" in n else [])})
        return out

    def networks(self, every=30):
        """the Wi-Fi networks around as last heard, answered at once: every sentence reads the device's lists, and
        a scan takes seconds, so it runs in the background, at most every 30 s (show wifi's own reading also
        refreshes it, hear)"""
        at, found = self._heard
        if time.time() - at > every and not (self._hearing and self._hearing.is_alive()):
            self._hearing = threading.Thread(target=self.hear, daemon=True)
            self._hearing.start()
        return found

    def hear(self, output=None):
        """the networks around, from a scan's output, or from a scan run now, as show wifi hears them"""
        if output is None:
            output = _run(["bash", "-c", self.wifi], timeout=20)
        self._heard = (time.time(), [{"value": n, "names": [n]} for n, _, _ in _wifi_list(output)])

    def _hosts(self):
        """the computers this device can reach with ssh by a name: each `Host` of ~/.ssh/config (the person's own
        ssh, not TermNL's home), without patterns. "studio-pi" can also be said "studio pi"."""
        out, seen = [], set()
        try:
            with open(os.path.expanduser("~/.ssh/config"), encoding="utf-8") as f:
                lines = f.read().splitlines()
        except OSError:
            return out
        for line in lines:
            parts = line.split()
            if len(parts) < 2 or parts[0].lower() != "host":
                continue
            for h in parts[1:]:
                if any(c in h for c in "*?!") or h.lower() in seen:
                    continue
                seen.add(h.lower())
                spoken = re.sub(r"[-_.]", " ", h)
                out.append({"value": h, "names": [h] + ([spoken] if spoken != h else [])})
        return out

    def forget(self):
        """after a command ran: the lists are read again next time (a folder just made is known)"""
        self._cache.clear()

    def list(self, kind):
        if kind == "network":
            return self.networks()
        read = {"folder": self._folders, "service": self._services, "app": self._apps, "music": self._music,
                "running": self._running, "host": self._hosts}.get(kind)
        if not read:
            return []
        at, found = self._cache.get(kind, (0, None))
        if found is None or time.time() - at > self.fresh:
            found = read()
            self._cache[kind] = (time.time(), found)
        return found

    def exists(self, value):
        return os.path.lexists(self.path(value))

    def files(self, folder):
        p = self.path(folder)
        try:
            return sorted(f for f in os.listdir(p) if not f.startswith(".") and os.path.isfile(os.path.join(p, f)))
        except OSError:
            return []

    def find(self, test):
        """every file under home whose name passes the test, hidden folders skipped"""
        out = []
        for root, dirs, files in os.walk(self.home):
            dirs[:] = sorted(d for d in dirs if not d.startswith("."))
            rel = os.path.relpath(root, self.home)
            folder = "$HOME" if rel == "." else "$HOME/" + rel
            label = "home" if rel == "." else os.path.basename(root)
            out += [{"folder": folder, "file": f, "label": label} for f in sorted(files) if not f.startswith(".") and test(f)]
        return out
