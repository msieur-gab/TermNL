"""The device read by itself, in words people use: @sys.temperature is "50 °C", not 50000.

A skill that only reads names its reader in its front matter (`reads: memory`) instead of a command.
Its replies use the reader's values ({@sys.memory.used}) and are chosen by the reader's level
("## When it's high"). A reader may also give a table, shown under the reply.

Each reader only reads (files under /proc and /sys, or a read-only command) and never changes the
device. The thresholds live here, written once per kind of board, so a skill author never needs them.
The words shown with a reading (table headings, "3 days and 2 hours"…) are the language's own
(words/readings.md), given to each reader as `w`."""
import datetime
import os
import platform
import subprocess

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


def _since(seconds, w):
    d, h, m = int(seconds // 86400), int(seconds % 86400 // 3600), int(seconds % 3600 // 60)
    parts = ([w("day" if d == 1 else "days", n=d)] if d else []) + ([w("hour" if h == 1 else "hours", n=h)] if h else [])
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
            [w("main disk row"), d["values"]["total"]], [w("running for"), _since(_uptime(), w)]]
    return {"level": "fine", "values": {"model": rows[0][1], "os": rows[1][1]}, "table": {"columns": ["", ""], "rows": rows}}


def health(w):
    """how the device is doing: the worst of temperature, memory and disk decides"""
    t, m, d = temperature(w), memory(w), storage(w)
    worst = "struggling" if t["level"] == "hot" or m["level"] == "full" or d["level"] == "full" else \
        "busy" if t["level"] == "warm" or m["level"] == "high" or d["level"] == "filling up" else "fine"
    levels = [t["level"], m["level"], d["level"], None]
    rows = [[w("temperature"), t["values"][""]], [w("memory"), w("memory used", used=m["values"]["used"], total=m["values"]["total"])],
            [w("main disk row"), w("disk free", free=d["values"]["free"], total=d["values"]["total"])], [w("running for"), _since(_uptime(), w)]]
    rows = [row + [w("level " + lv) if lv else ""] for row, lv in zip(rows, levels)]
    return {"level": worst, "values": {"temperature": t["values"][""], "memory": m["values"]["percent"], "disk": d["values"]["percent"],
                                       "uptime": _since(_uptime(), w)},
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


# name → (reader, its levels, its values; "" is the main one: {@sys.temperature})
READERS = {
    "memory": (memory, ["fine", "high", "full"], ["used", "total", "free", "percent"]),
    "temperature": (temperature, ["fine", "warm", "hot", "unknown"], ["", "max"]),
    "storage": (storage, ["fine", "filling up", "full"], ["free", "total", "percent"]),
    "processes": (processes, ["fine"], ["top", "count"]),
    "system": (system, ["fine"], ["model", "os"]),
    "folder": (folder, ["fine", "empty"], ["count"]),
    "health": (health, ["fine", "busy", "struggling"], ["temperature", "memory", "disk", "uptime"]),
}


def read(name, words=None, **args):
    """→ {level, values: {"@sys.<name>.<value>": text, "@sys.<name>": main}, table?}; words: readings.md"""
    r = READERS[name][0](words if isinstance(words, Words) else Words(words), **args)
    r["values"] = {placeholder(name, k): v for k, v in r["values"].items()}
    return r


def placeholder(name, value):
    return "@sys.%s.%s" % (name, value) if value else "@sys." + name
