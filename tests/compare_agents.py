"""python3 -m tests.compare_agents [-v] — agent.py and back_agent.py, side by side, reply by reply.

Plays the same conversations through both: the test conversations and the phrasings (pretend device),
and every turn people typed (logs/, read against this machine's own lists, with admin mode and show
commands on). Nothing runs: the agents only answer. Any reply that differs is printed."""
import glob
import json
import os
import re
import sys

from termnl import agent as v2
from termnl import back_agent as v1
from termnl.device import Device
from termnl.load import ROOT, load_language, load_settings
from tests.device import device as pretend

lang = load_language("en")
here = os.path.join(ROOT, "tests")
conversations = [(s, t, pretend) for s, t in json.load(open(os.path.join(here, "conversations.json"), encoding="utf-8"))]
conversations += [({"admin mode": "on"}, [m.group(1)], pretend) for m in
                  (re.match(r"^- [\w-]+: (.+)$", l) for l in open(os.path.join(here, "phrasings.md"), encoding="utf-8").read().split("\n")) if m]
real = Device(load_settings().get("home") or "~/TermNL-home", home_names=[" ".join(p) for p in lang["lists"]["conversation"]["home folder"]])
for f in sorted(glob.glob(os.path.join(ROOT, "logs", "*.jsonl"))):
    by = {}
    for line in open(f, encoding="utf-8"):
        d = json.loads(line)
        by.setdefault(d["session"], []).append(d["text"])
    conversations += [({"admin mode": "on", "show commands": "on"}, turns, real) for turns in by.values()]

turns = differ = 0
for settings, said, dev in conversations:
    a = v1.Agent(**lang, settings=dict(settings), device=dev, random=lambda: 0)
    b = v2.Agent(**lang, settings=dict(settings), device=dev, random=lambda: 0)
    for t in said:
        turns += 1
        ra, rb = a.hear(t), b.hear(t)
        same = ra == rb and (a.pending is None) == (b.pending is None) and a.here == b.here
        if not same:
            differ += 1
            print("DIFF %r\n  v1: %s\n  v2: %s" % (t, ra, rb))
        elif "-v" in sys.argv:
            print("same %r → %s" % (t, ra.get("say")))
print("%d conversations, %d turns compared, %d differ" % (len(conversations), turns, differ))
sys.exit(1 if differ else 0)
