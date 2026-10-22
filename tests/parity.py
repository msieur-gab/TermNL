"""python3 -m tests.parity — the Python agent gives the JavaScript agent's replies, turn by turn (needs node)."""
import json
import os
import re
import subprocess

from termnl.agent import Agent
from termnl.load import ROOT, load_language
from tests.device import device

here = os.path.join(ROOT, "tests")
lang = load_language("en")
convs = json.load(open(os.path.join(here, "conversations.json"), encoding="utf-8"))
phr = [[{"admin mode": "on"}, [m.group(1)]] for m in (re.match(r"^- [\w-]+: (.+)$", l) for l in open(os.path.join(here, "phrasings.md"), encoding="utf-8").read().split("\n")) if m]
js = json.loads(subprocess.run(["node", os.path.join(here, "parity.mjs")], capture_output=True, text=True, check=True).stdout)
keys = ["outcome", "skill", "say", "command", "chips", "show", "how", "unknown"]
diff = turns = 0
for (settings, ts), jconv in zip(convs + phr, js):
    a = Agent(**lang, settings=settings, device=device, random=lambda: 0)
    for t, j in zip(ts, jconv):
        turns += 1
        r = a.hear(t)
        p = {k: r.get(k) for k in keys}
        if p != j:
            diff += 1
            print("DIFF", repr(t), "\n  js:", j, "\n  py:", p)
print("%d turns compared, %d differ" % (turns, diff))
