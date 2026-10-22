"""The device read by itself, in words people use: @sys.temperature is "50 °C", not 50000.

A skill that only reads names its reader in its front matter (`reads: memory`) instead of a command.
Its replies use the reader's values ({@sys.memory.used}) and are chosen by the reader's level
("## When it's high"). A reader may also give a table, shown under the reply.

Each reader only reads (files under /proc and /sys, or a read-only command) and never changes the
device. The thresholds live here, written once per kind of board, so a skill author never needs them."""
import datetime
import os
import platform
import subprocess


def _size(kb):
    b = kb * 1024
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024 or unit == "TB":
            return ("%.1f %s" % (b, unit)).replace(".0 ", " ")
        b /= 1024


def _meminfo():
    out = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, v = line.split(":", 1)
            out[k] = int(v.split()[0])
    return out


def _since(seconds):
    d, h, m = int(seconds // 86400), int(seconds % 86400 // 3600), int(seconds % 3600 // 60)
    parts = (["%d day%s" % (d, "s" * (d != 1))] if d else []) + (["%d hour%s" % (h, "s" * (h != 1))] if h else [])
    return " and ".join(parts) if parts else "%d minute%s" % (m, "s" * (m != 1))


def _uptime():
    with open("/proc/uptime") as f:
        return float(f.read().split()[0])


def memory():
    m = _meminfo()
    used = m["MemTotal"] - m["MemAvailable"]
    percent = round(100 * used / m["MemTotal"])
    level = "fine" if percent < 75 else "high" if percent < 90 else "full"
    return {"level": level, "values": {"used": _size(used), "total": _size(m["MemTotal"]), "free": _size(m["MemAvailable"]), "percent": "%d%%" % percent}}


# the processor's sensor, by the names boards and laptops give it, before any other zone
CPU_SENSORS = ("x86_pkg_temp", "cpu-thermal", "cpu_thermal", "soc-thermal", "soc_thermal", "cpu", "k10temp", "coretemp")
HOT = 80  # most boards slow down (throttle) around here; a Raspberry Pi from 80–85 °C


def temperature():
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
        return {"level": "unknown", "values": {"": "unknown", "max": "%d °C" % HOT}}
    cpu = next((t for name in CPU_SENSORS for kind, t in zones if kind.lower().startswith(name)), None)
    t = cpu if cpu is not None else max(t for _, t in zones)
    level = "fine" if t < HOT - 10 else "warm" if t < HOT else "hot"
    return {"level": level, "values": {"": "%d °C" % round(t), "max": "%d °C" % HOT}}


# what counts as a disk: real filesystems, not the system's own virtual ones
DISK_TYPES = ("ext4", "ext3", "ext2", "btrfs", "xfs", "vfat", "exfat", "ntfs", "ntfs3", "f2fs")


def storage():
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
            rows.append(["the main disk" if where == "/" else where, _size(total), _size(total - free), _size(free), "%d%%" % percent])
            if where == "/":
                root = (total, free, percent)
    total, free, percent = root or (0, 0, 0)
    level = "fine" if percent < 80 else "filling up" if percent < 95 else "full"
    return {"level": level, "values": {"free": _size(free), "total": _size(total), "percent": "%d%%" % percent},
            "table": {"columns": ["Disk", "Size", "Used", "Free", "Full"], "rows": rows}}


def processes(top=8):
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
    rows = [[name, _size(mem), "%d%%" % round(cpu), str(n)] for name, (mem, cpu, n) in ranked[:top]]
    first = ranked[0][0] if ranked else "nothing"
    return {"level": "fine", "values": {"top": first, "count": str(sum(n for _, (_, _, n) in by.items()))},
            "table": {"columns": ["Program", "Memory", "Processor", "Processes"], "rows": rows}}


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


def system():
    """what the device is: its model, system, processor, memory and disk"""
    m, d = memory(), storage()
    rows = [["Device", _model()], ["System", _os()], ["Kernel", platform.release()],
            ["Processor", "%s (%d cores)" % (_cpu(), os.cpu_count() or 1)], ["Memory", m["values"]["total"]],
            ["Main disk", d["values"]["total"]], ["Running for", _since(_uptime())]]
    return {"level": "fine", "values": {"model": rows[0][1], "os": rows[1][1]}, "table": {"columns": ["", ""], "rows": rows}}


def health():
    """how the device is doing: the worst of temperature, memory and disk decides"""
    t, m, d = temperature(), memory(), storage()
    worst = "struggling" if t["level"] == "hot" or m["level"] == "full" or d["level"] == "full" else \
        "busy" if t["level"] == "warm" or m["level"] == "high" or d["level"] == "filling up" else "fine"
    rows = [["Temperature", t["values"][""], t["level"]], ["Memory", "%s of %s used" % (m["values"]["used"], m["values"]["total"]), m["level"]],
            ["Main disk", "%s free of %s" % (d["values"]["free"], d["values"]["total"]), d["level"]], ["Running for", _since(_uptime()), ""]]
    return {"level": worst, "values": {"temperature": t["values"][""], "memory": m["values"]["percent"], "disk": d["values"]["percent"],
                                       "uptime": _since(_uptime())},
            "table": {"columns": ["", "Now", ""], "rows": rows}}


def folder(place):
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
        kind = "folder" if is_dir else (os.path.splitext(n)[1][1:].lower() + " file" if "." in n else "file")
        when = datetime.datetime.fromtimestamp(st.st_mtime)
        changed = when.strftime("today %H:%M") if when.date() == today else when.strftime("%-d %b %Y")
        rows.append([n, kind, "" if is_dir else _size(st.st_size // 1024 or (1 if st.st_size else 0)), changed])
    more = len(rows) - 30
    rows = rows[:30] + ([["… and %d more" % more, "", "", ""]] if more > 0 else [])
    return {"level": "fine" if names else "empty", "values": {"count": str(len(names))},
            "table": {"columns": ["Name", "Kind", "Size", "Changed"], "rows": rows} if names else None}


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


def read(name, **args):
    """→ {level, values: {"@sys.<name>.<value>": text, "@sys.<name>": main}, table?}"""
    r = READERS[name][0](**args)
    r["values"] = {placeholder(name, k): v for k, v in r["values"].items()}
    return r


def placeholder(name, value):
    return "@sys.%s.%s" % (name, value) if value else "@sys." + name
