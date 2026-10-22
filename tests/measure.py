"""python3 -m tests.measure [-v] — how many hand-written phrasings TermNL understands, and how it answers;
then, if tests/real.md is here, how the conversations people really had go today (tests/real.py).
It looks at the skill only, not the values: see the review of 22 Oct 2026."""
import os
import re
import sys

from termnl.agent import Agent
from termnl.load import ROOT, load_language
from tests.device import device

lang = load_language("en")
with open(os.path.join(ROOT, "tests", "phrasings.md"), encoding="utf-8") as f:
    lines = [m.groups() for m in (re.match(r"^- ([\w-]+): (.+)$", l) for l in f.read().split("\n")) if m]
tally = {"acted": 0, "asked": 0, "wrong?": 0, "WRONG": 0, "abstain": 0}
for want, text in lines:
    r = Agent(**lang, settings={"admin mode": "on"}, device=device, random=lambda: 0).hear(text)
    got = r.get("skill") or ("choose" if r["outcome"] == "ask" and r.get("chips") else "—")
    if r["outcome"] == "abstain" and not r.get("skill"):
        kind = "abstain"
    elif got != want:
        kind = "wrong?" if r["outcome"] == "ask" else "WRONG"
    else:
        kind = "asked" if r["outcome"] == "ask" and r.get("chips") and r["chips"][0] == "yes" else "acted"
    tally[kind] += 1
    if "-v" in sys.argv or kind != "acted":
        new = "   [new: %s]" % ", ".join(r["unknown"]) if r.get("unknown") else ""
        print("%-8s %-18s %-18s %s%s" % (kind, want, got, text, new))
print('\n%d phrasings: %d understood and handled, %d understood but checked first ("Do you want me to…?"), %d wrong skill but asked first, '
      '%d wrong skill acted on or approved, %d not understood' % (len(lines), tally["acted"], tally["asked"], tally["wrong?"], tally["WRONG"], tally["abstain"]))

# the sentences people really typed (tests/real.md, kept out of git), apart from these: python3 -m tests.real
if os.path.exists(os.path.join(ROOT, "tests", "real.md")):
    import contextlib
    import io
    from tests import real
    with contextlib.redirect_stdout(io.StringIO()):
        tally = real.replay()
    print(real.summary(tally))
