"""python3 -m tests.measure [set] [-v] — how many sentences TermNL understands, and how it answers.

    set   phrasings (default): tests/phrasings.md, hand-written on 22 Oct, partly tuned against
          probes:    tests/probes.md, written 24 Oct to diagnose, tuned against (optimistic)
          heldout:   tests/heldout.md, written 24 Oct before any change, never tuned against
          all:       the three, one after the other

A line `- none: …` is a sentence TermNL should not act on: abstaining is right, asking is harmless, acting
is wrong. Then, with the default set and if tests/real.md is here, the conversations people really had
(tests/real.py). It looks at the skill only, not the values: see the review of 22 Oct 2026."""
import os
import re
import sys

from termnl.agent import Agent
from termnl.load import ROOT, load_language
from tests.device import device

SETS = ("phrasings", "probes", "heldout", "blind")


def lines_of(name):
    with open(os.path.join(ROOT, "tests", name + ".md"), encoding="utf-8") as f:
        return [m.groups() for m in (re.match(r"^- ([\w-]+): (.+)$", l) for l in f.read().split("\n")) if m]


def kind_of(want, r):
    asked_first = r["outcome"] == "ask" and r.get("chips") and r["chips"][0] == "yes"
    if want == "none":
        if r["outcome"] in ("act", "approve") and r.get("skill"):
            return "WRONG"
        return "asked" if r["outcome"] == "ask" else "abstain"
    got = r.get("skill") or ("choose" if r["outcome"] == "ask" and r.get("chips") else "—")
    if r["outcome"] == "abstain" and not r.get("skill"):
        return "abstain"
    if got != want:
        return "wrong?" if r["outcome"] == "ask" else "WRONG"
    return "asked" if asked_first else "acted"


def measure(name, lang, verbose=False, quiet=False):
    lines = lines_of(name)
    tally = {"acted": 0, "asked": 0, "wrong?": 0, "WRONG": 0, "abstain": 0, "none": 0, "none abstain": 0, "none asked": 0, "none WRONG": 0}
    for want, text in lines:
        r = Agent(**lang, settings={"admin mode": "on"}, device=device, random=lambda: 0).hear(text)
        kind = kind_of(want, r)
        if want == "none":
            tally["none"] += 1
            tally["none " + kind] += 1
        else:
            tally[kind] += 1
        if not quiet and (verbose or kind not in ("acted",) and not (want == "none" and kind == "abstain")):
            got = r.get("skill") or "—"
            new = "   [new: %s]" % ", ".join(r["unknown"]) if r.get("unknown") else ""
            print("%-8s %-18s %-18s %s%s" % (kind, want, got, text, new))
    return tally


def summary(name, t):
    n = t["acted"] + t["asked"] + t["wrong?"] + t["WRONG"] + t["abstain"]
    out = ('%s, %d sentences: %d understood and handled, %d understood but checked first ("Do you want me to…?"), '
           '%d wrong skill but asked first, %d wrong skill acted on or approved, %d not understood' %
           (name, n, t["acted"], t["asked"], t["wrong?"], t["WRONG"], t["abstain"]))
    if t["none"]:
        out += "; out of scope, %d: %d abstained, %d asked, %d acted on" % (t["none"], t["none abstain"], t["none asked"], t["none WRONG"])
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    name = args[0] if args else "phrasings"
    lang = load_language("en")
    for s in SETS if name == "all" else (name,):
        t = measure(s, lang, verbose="-v" in sys.argv, quiet=name == "all" and "-v" not in sys.argv)
        print(("\n" if name != "all" else "") + summary(s, t))

    # the sentences people really typed (tests/real.md, kept out of git), apart from these: python3 -m tests.real
    if name == "phrasings" and os.path.exists(os.path.join(ROOT, "tests", "real.md")):
        import contextlib
        import io
        from tests import real
        with contextlib.redirect_stdout(io.StringIO()):
            tally = real.replay()
        print(real.summary(tally))
