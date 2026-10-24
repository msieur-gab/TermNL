"""The device read by itself, in words people use: @sys.temperature is "50 °C", not 50000.

A skill that only reads names its reader in its front matter (`reads: memory`) instead of a command.
Its replies use the reader's values ({@sys.memory.used}) and are chosen by the reader's level
("## When it's high"). A reader may also give a table, shown under the reply.

Each reader only reads (files under /proc and /sys, the kernel's own answers, a read-only command, or
the output of its skill's own command) and never changes the device. The thresholds live here, written once per kind of board, so a skill author never needs them.
The words shown with a reading (table headings, "3 days and 2 hours"…) are the language's own
(words/readings.md), given to each reader as `w`."""
import ctypes
import ctypes.util
import datetime
import os
import platform
import re
import subprocess
import time

from .text import fill


class Words:
    """w("disk") → "Disk"; w("days", n=3) → "3 days"; a word missing from readings.md shows its name"""
    def __init__(self, pairs=None):
        self.pairs = pairs or {}

    def __call__(self, key, **values):
        return fill(self.pairs.get(key, key), values)

    def list(self, key, default):
        return [x.strip() for x in self.pairs[key].split(",")] if key in self.pairs else default


def _size(kb, w):
    b = kb * 1024
    units = w.list("units", ["B", "KB", "MB", "GB", "TB"])
    for i, unit in enumerate(units):
        if b < 1024 or i == len(units) - 1:
            return ("%.1f %s" % (b, unit)).replace(".0 ", " ")
        b /= 1024


def _meminfo():
    out = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, v = line.split(":", 1)
            out[k] = int(v.split()[0])
    return out


def since(seconds, w):
    d, h, m = int(seconds // 86400), int(seconds % 86400 // 3600), int(seconds % 3600 // 60)
    parts = ([w("day" if d == 1 else "days", n=d)] if d else []) + ([w("hour" if h == 1 else "hours", n=h)] if h else [])
    if not parts and not m:  # under a minute (a training on the laptop)
        s = int(seconds)
        return w("second" if s == 1 else "seconds", n=s)
    if not parts:
        return w("minute" if m == 1 else "minutes", n=m)
    return w("and", a=parts[0], b=parts[1]) if len(parts) == 2 else parts[0]


def _uptime():
    with open("/proc/uptime") as f:
        return float(f.read().split()[0])


def memory(w):
    m = _meminfo()
    used = m["MemTotal"] - m["MemAvailable"]
    percent = round(100 * used / m["MemTotal"])
    level = "fine" if percent < 75 else "high" if percent < 90 else "full"
    return {"level": level, "values": {"used": _size(used, w), "total": _size(m["MemTotal"], w), "free": _size(m["MemAvailable"], w), "percent": "%d%%" % percent}}


# the processor's sensor, by the names boards and laptops give it, before any other zone
CPU_SENSORS = ("x86_pkg_temp", "cpu-thermal", "cpu_thermal", "soc-thermal", "soc_thermal", "cpu", "k10temp", "coretemp")
HOT = 80  # most boards slow down (throttle) around here; a Raspberry Pi from 80–85 °C


def temperature(w):
    zones = []
    for z in sorted(os.listdir("/sys/class/thermal")) if os.path.isdir("/sys/class/thermal") else []:
        try:
            with open("/sys/class/thermal/%s/type" % z) as f:
                kind = f.read().strip()
            with open("/sys/class/thermal/%s/temp" % z) as f:
                zones.append((kind, int(f.read().strip()) / 1000))
        except (OSError, ValueError):
            continue
    if not zones:
        return {"level": "unknown", "values": {"": w("unknown"), "max": "%d °C" % HOT}}
    cpu = next((t for name in CPU_SENSORS for kind, t in zones if kind.lower().startswith(name)), None)
    t = cpu if cpu is not None else max(t for _, t in zones)
    level = "fine" if t < HOT - 10 else "warm" if t < HOT else "hot"
    return {"level": level, "values": {"": "%d °C" % round(t), "max": "%d °C" % HOT}}


# what counts as a disk: real filesystems, not the system's own virtual ones
DISK_TYPES = ("ext4", "ext3", "ext2", "btrfs", "xfs", "vfat", "exfat", "ntfs", "ntfs3", "f2fs")


def storage(w):
    rows, root = [], None
    seen = set()
    with open("/proc/mounts") as f:
        for line in f:
            dev, where, kind = line.split()[:3]
            if kind not in DISK_TYPES or dev in seen or where.startswith("/snap"):
                continue
            seen.add(dev)
            try:
                s = os.statvfs(where)
            except OSError:
                continue
            total, free = s.f_blocks * s.f_frsize // 1024, s.f_bavail * s.f_frsize // 1024
            percent = round(100 * (total - free) / total) if total else 0
            rows.append([w("main disk") if where == "/" else where, _size(total, w), _size(total - free, w), _size(free, w), "%d%%" % percent])
            if where == "/":
                root = (total, free, percent)
    total, free, percent = root or (0, 0, 0)
    level = "fine" if percent < 80 else "filling up" if percent < 95 else "full"
    return {"level": level, "values": {"free": _size(free, w), "total": _size(total, w), "percent": "%d%%" % percent},
            "table": {"columns": [w("disk"), w("size"), w("used"), w("free"), w("full")], "rows": rows}}


def processes(w, top=8):
    """the programs using the most memory, their processes added together (a browser has many)"""
    out = subprocess.run(["ps", "-eo", "comm,rss,pcpu", "--no-headers"], capture_output=True, text=True, timeout=5).stdout
    by = {}
    for line in out.splitlines():
        parts = line.rsplit(None, 2)
        if len(parts) != 3:
            continue
        name, rss, cpu = parts[0].strip(), int(parts[1]), float(parts[2])
        mem, c, n = by.get(name, (0, 0.0, 0))
        by[name] = (mem + rss, c + cpu, n + 1)
    ranked = sorted(by.items(), key=lambda x: -x[1][0])
    rows = [[name, _size(mem, w), "%d%%" % round(cpu), str(n)] for name, (mem, cpu, n) in ranked[:top]]
    first = ranked[0][0] if ranked else w("nothing")
    return {"level": "fine", "values": {"top": first, "count": str(sum(n for _, (_, _, n) in by.items()))},
            "table": {"columns": [w("program"), w("memory"), w("processor"), w("processes")], "rows": rows}}


def _model():
    for path in ("/proc/device-tree/model", "/sys/class/dmi/id/product_name"):
        try:
            with open(path) as f:
                name = f.read().strip("\x00\n ")
            if name:
                if path.endswith("product_name"):
                    with open("/sys/class/dmi/id/sys_vendor") as v:
                        vendor = v.read().strip()
                    return ("%s %s" % (vendor, name)).strip()
                return name
        except OSError:
            continue
    return platform.node()


def _os():
    try:
        with open("/etc/os-release") as f:
            pairs = dict(l.rstrip("\n").split("=", 1) for l in f if "=" in l)
        return pairs.get("PRETTY_NAME", "Linux").strip('"')
    except OSError:
        return "Linux"


def _cpu():
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.lower().startswith(("model name", "hardware")):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.machine()


def system(w):
    """what the device is: its model, system, processor, memory and disk"""
    m, d = memory(w), storage(w)
    rows = [[w("device"), _model()], [w("system"), _os()], [w("kernel"), platform.release()],
            [w("processor"), w("cores", cpu=_cpu(), count=os.cpu_count() or 1)], [w("memory"), m["values"]["total"]],
            [w("main disk row"), d["values"]["total"]], [w("running for"), since(_uptime(), w)]]
    return {"level": "fine", "values": {"model": rows[0][1], "os": rows[1][1]}, "table": {"columns": ["", ""], "rows": rows}}


def health(w):
    """how the device is doing: the worst of temperature, memory and disk decides"""
    t, m, d = temperature(w), memory(w), storage(w)
    worst = "struggling" if t["level"] == "hot" or m["level"] == "full" or d["level"] == "full" else \
        "busy" if t["level"] == "warm" or m["level"] == "high" or d["level"] == "filling up" else "fine"
    levels = [t["level"], m["level"], d["level"], None]
    rows = [[w("temperature"), t["values"][""]], [w("memory"), w("memory used", used=m["values"]["used"], total=m["values"]["total"])],
            [w("main disk row"), w("disk free", free=d["values"]["free"], total=d["values"]["total"])], [w("running for"), since(_uptime(), w)]]
    rows = [row + [w("level " + lv) if lv else ""] for row, lv in zip(rows, levels)]
    return {"level": worst, "values": {"temperature": t["values"][""], "memory": m["values"]["percent"], "disk": d["values"]["percent"],
                                       "uptime": since(_uptime(), w)},
            "table": {"columns": ["", w("now"), ""], "rows": rows, "levels": levels}}


def folder(w, place):
    """what a folder holds: folders first, then files, newest change shown as a date"""
    try:
        names = sorted(n for n in os.listdir(place) if not n.startswith("."))
    except OSError:
        names = []
    rows = []
    today = datetime.date.today()
    for n in sorted(names, key=lambda n: (not os.path.isdir(os.path.join(place, n)), n.lower())):
        p = os.path.join(place, n)
        try:
            st = os.stat(p)
        except OSError:
            continue
        is_dir = os.path.isdir(p)
        kind = w("folder") if is_dir else (w("file of a type", ext=os.path.splitext(n)[1][1:].lower()) if "." in n else w("file"))
        when = datetime.datetime.fromtimestamp(st.st_mtime)
        months = w.list("months", [])
        month = months[when.month - 1] if len(months) == 12 else when.month
        changed = w("today", time=when.strftime("%H:%M")) if when.date() == today else w("date", day=when.day, month=month, year=when.year)
        rows.append([n, kind, "" if is_dir else _size(st.st_size // 1024 or (1 if st.st_size else 0), w), changed])
    more = len(rows) - 30
    rows = rows[:30] + ([[w("more", count=more), "", "", ""]] if more > 0 else [])
    return {"level": "fine" if names else "empty", "values": {"count": str(len(names))},
            "table": {"columns": [w("name"), w("kind"), w("size"), w("changed")], "rows": rows} if names else None}


# a clock earlier than this can't be right: TermNL was written in 2026. A board without a clock battery
# can wake up in 1970, or on the day its system image was made, after a power cut.
MADE = 2026


def _synchronised():
    """the kernel's own answer: has a time service (NTP) set the clock? None when it can't tell"""
    try:
        libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6", use_errno=True)
        timex = ctypes.create_string_buffer(512)  # struct timex, all zero: only read, change nothing
        state = libc.adjtimex(timex)
    except (OSError, AttributeError):
        return None
    return None if state < 0 else state != 5  # 5: TIME_ERROR, the clock is not synchronised


def clock(w):
    """the time, the day and the date, and whether the clock can be trusted"""
    now = datetime.datetime.now()
    days, months = w.list("weekdays", []), w.list("months in full", [])
    day = days[now.weekday()] if len(days) == 7 else now.strftime("%A")
    month = months[now.month - 1] if len(months) == 12 else now.month
    synced = _synchronised()
    level = "wrong" if now.year < MADE else "unsure" if synced is False else "fine"
    return {"level": level, "values": {"": w("clock time", hour=now.strftime("%H"), minute=now.strftime("%M")), "day": day,
                                       "date": w("clock date", day=now.day, month=month, year=now.year)}}


# TermNL reads itself too: the server gives what only it knows (server.py, state)

def learning(w, started=None, trained=None):
    """learning again now, for how long so far; or when the model in use was trained (train.py writes it in)"""
    now = time.time()
    if started:
        return {"level": "learning", "values": {"": since(now - started, w)}}
    return {"level": "fine" if trained else "unknown", "values": {"": since(now - trained, w) if trained else ""}}


def name(w, user=""):
    """the person's name, when they gave one ("call me Gab")"""
    return {"level": "known" if user else "unknown", "values": {"": user}}


# Wi-Fi, the network and Bluetooth have no file to read: their skill's command runs (and is what "show
# commands" shows), and these readers turn its output into words. Each gets it as `output`.
FROM_COMMAND = ("wifi", "networks", "network", "bluetooth")
WEAK = 40  # a Wi-Fi signal under this (of 100) drops and slows down


def _quality(dbm):
    """a signal in dBm → of 100, as NetworkManager counts it: -50 dBm or stronger is 100, -100 is 0"""
    return max(0, min(100, 2 * (round(dbm) + 100)))


def _ssid(name):
    """iw writes a name's other bytes as \\xNN (Café is Caf\\xc3\\xa9); a hidden network's are all zero"""
    if "\\x" in name:
        name = name.encode("latin-1", "replace").decode("unicode_escape").encode("latin-1").decode("utf-8", "replace")
    return name.strip("\x00").strip()


def _wifi_list(output):
    """`iw dev <wifi> link`, then `iw dev <wifi> scan dump` → [(name, signal of 100, in use)], one per name:
    the one in use with the signal it has now (link), the others with their strongest access point (a
    network often has several). Without root, the scan dump is what the device heard last, not a new scan."""
    blocks = []
    for line in output.splitlines():
        if line.startswith(("Connected to ", "BSS ")):
            blocks.append({"link": line.startswith("Connected"), "used": line.startswith("Connected") or "associated" in line})
        elif blocks:
            name = re.match(r"\tSSID: (.*)$", line)
            signal = re.match(r"\tsignal: .*?(-\d+(?:\.\d+)?) dBm", line)  # one board's driver writes "0.-75 dBm"
            if name and "name" not in blocks[-1]:
                blocks[-1]["name"] = _ssid(name.group(1))
            if signal:
                blocks[-1]["signal"] = _quality(float(signal.group(1)))
    best = {}
    for b in blocks:
        if not b.get("name") or "signal" not in b:
            continue  # a hidden network has no name
        old = best.get(b["name"])
        if not old or b["link"] or (not old["link"] and (b["used"], b["signal"]) > (old["used"], old["signal"])):
            best[b["name"]] = b
    found = [(b["name"], b["signal"], b["used"]) for b in best.values()]
    return sorted(found, key=lambda n: (-n[1], not n[2]))  # strongest first; the one in use first among equals


def wifi(w, output=""):
    """the Wi-Fi network this device is on, and how strong its signal is"""
    found = _wifi_list(output)
    on = next((n for n in found if n[2]), None)
    if on:
        level = "fine" if on[1] >= WEAK else "weak"
        return {"level": level, "values": {"": on[0], "signal": "%d%%" % on[1], "count": str(len(found))}}
    return {"level": "not connected" if found else "off", "values": {"": w("nothing"), "signal": "", "count": str(len(found))}}


def networks(w, output="", top=15):
    """the Wi-Fi networks around, strongest first"""
    found = _wifi_list(output)
    if not found:
        return {"level": "none", "values": {"count": "0", "best": w("nothing")}, "table": None}
    rows = [[w("connected name", name=n) if used else n, "%d%%" % sig, w("signal " + ("good" if sig >= WEAK else "weak"))] for n, sig, used in found[:top]]
    levels = [None if sig >= WEAK else "weak" for _, sig, _ in found[:top]]
    more = len(found) - top
    if more > 0:
        rows.append([w("more", count=more), "", ""])
        levels.append(None)
    return {"level": "fine", "values": {"count": str(len(found)), "best": found[0][0]},
            "table": {"columns": [w("network"), w("signal"), ""], "rows": rows, "levels": levels}}


# connections that aren't a way out of the device: itself, and the bridges of containers and virtual machines
NOT_A_LINK = ("lo", "docker", "br-", "virbr", "veth")


def _link(name, w):
    """what people call a connection: wlan0 → Wi-Fi, eth0 → cable"""
    kind = "wifi link" if name.startswith(("wl", "wlan")) else "cable link" if name.startswith(("en", "eth")) else \
        "usb link" if name.startswith("usb") else None
    return w(kind) if kind else name


def network(w, output=""):
    """connected to a network: an address on a connection that is up. Nothing leaves the device to ask
    whether the internet answers."""
    rows = []
    for line in output.splitlines():
        f = line.split()
        if len(f) < 3 or f[0].startswith(NOT_A_LINK) or f[1] == "DOWN":
            continue
        rows.append([_link(f[0].split("@")[0], w), f[2].split("/")[0]])
    if not rows:
        return {"level": "not connected", "values": {"address": "", "through": ""}, "table": None}
    return {"level": "connected", "values": {"address": rows[0][1], "through": rows[0][0]},
            "table": {"columns": [w("connection"), w("address")], "rows": rows} if len(rows) > 1 else None}


def bluetooth(w, output=""):
    """bluetoothctl show: is Bluetooth on, and the name others see"""
    pairs = dict(l.strip().split(": ", 1) for l in output.splitlines() if ": " in l)
    if not output.strip().startswith("Controller"):
        return {"level": "none", "values": {"name": ""}}
    return {"level": "on" if pairs.get("Powered") == "yes" else "off", "values": {"name": pairs.get("Alias") or pairs.get("Name", "")}}


# name → (reader, its levels, its values; "" is the main one: {@sys.temperature})
READERS = {
    "memory": (memory, ["fine", "high", "full"], ["used", "total", "free", "percent"]),
    "temperature": (temperature, ["fine", "warm", "hot", "unknown"], ["", "max"]),
    "storage": (storage, ["fine", "filling up", "full"], ["free", "total", "percent"]),
    "processes": (processes, ["fine"], ["top", "count"]),
    "system": (system, ["fine"], ["model", "os"]),
    "folder": (folder, ["fine", "empty"], ["count"]),
    "health": (health, ["fine", "busy", "struggling"], ["temperature", "memory", "disk", "uptime"]),
    "clock": (clock, ["fine", "unsure", "wrong"], ["", "day", "date"]),
    "learning": (learning, ["learning", "fine", "unknown"], [""]),
    "name": (name, ["known", "unknown"], [""]),
    "wifi": (wifi, ["fine", "weak", "not connected", "off"], ["", "signal", "count"]),
    "networks": (networks, ["fine", "none"], ["count", "best"]),
    "network": (network, ["connected", "not connected"], ["address", "through"]),
    "bluetooth": (bluetooth, ["on", "off", "none"], ["name"]),
}


def read(name, words=None, **args):
    """→ {level, values: {"@sys.<name>.<value>": text, "@sys.<name>": main}, table?}; words: readings.md"""
    r = READERS[name][0](words if isinstance(words, Words) else Words(words), **args)
    r["values"] = {placeholder(name, k): v for k, v in r["values"].items()}
    return r


def placeholder(name, value):
    return "@sys.%s.%s" % (name, value) if value else "@sys." + name
