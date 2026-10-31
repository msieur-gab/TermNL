"""python3 -m tools.gate [ref] — what a change does, sentence by sentence, before it is pushed. The working copy
is compared with ref (default: HEAD, the last commit): the same sentences go through both, and every one whose
answer moved is listed, the better and the worse, never only the totals (Gab, 31 Oct: "a sign that something is
slowly derailing").

First the conversations people really had (tests/real.md, kept out of git: python3 -m tests.real --add), replayed
turn by turn, then every test set of tests/measure.py, each sentence matched by its words (a new skill's tests.md
moves the others). It fails on:
  - a test sentence that now acts on, or asks approval for, the wrong skill (a new wrong action);
  - a real turn whose "should" it met before and doesn't now.
A real turn without a "should" can't be judged: one that now acts on another skill, or acts where it asked, is
listed under "look at each" for a person to judge. Nothing is written in either copy: the replay keeps "call me
…" in memory and never retrains (tests/real.py).

    ref           any commit, branch or tag: the copy before the change
    --keep        keeps the copy of ref (in the system's temporary folder) instead of removing it"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL = os.path.join(HERE, "tests", "real.md")
RANK = {"acted": 3, "asked": 2, "abstain": 1, "wrong?": 1, "WRONG": 0}  # a sentence for a skill
RANK_NONE = {"abstain": 2, "asked": 1, "WRONG": 0}  # an out-of-scope sentence: abstaining is right, acting is wrong


def answers(root, real_md):
    """every answer of the TermNL in root: its real turns, then each test set → {"real": […], "sets": […]}.
    Run in a process of its own, with root first on the path, so a copy from before this file still answers."""
    sys.path.insert(0, root)
    os.chdir(root)
    import random
    from termnl.agent import Agent
    from termnl.load import load_language
    from tests import measure, real
    from tests.device import device

    out = {"real": [], "sets": []}
    if os.path.exists(real_md):
        real.HERE = real_md
        real.Replay.set = lambda self, key, value: self.settings.__setitem__(key, value)  # a copy from before the fix
        start, conversations = real.parse(open(real_md, encoding="utf-8").read())
        home = tempfile.mkdtemp(prefix="termnl-gate-")
        try:
            for p in start:
                path = os.path.join(home, p.rstrip("/"))
                os.makedirs(path if p.endswith("/") else os.path.dirname(path), exist_ok=True)
                if not p.endswith("/"):
                    open(path, "a").close()
            app = real.Replay(home)
            app.trainer = ["true"]
            random.seed(0)
            for n, c in enumerate(conversations):
                for t in c["turns"]:
                    r = app.say(t["you"], "conversation %d" % n)
                    out["real"].append({"where": c["title"], "you": t["you"], "outcome": r["outcome"], "skill": r.get("skill") or "",
                                        "say": (r.get("say") or "").replace("\n", " ")[:90],
                                        "met": None if "should" not in t else not real.judge(t["should"], r)})
        finally:
            shutil.rmtree(home, ignore_errors=True)
    lang = load_language("en")
    for name in measure.SETS:
        for want, text in measure.lines_of(name):
            r = Agent(**lang, settings={"admin mode": "on"}, device=device, random=lambda: 0).hear(text)
            out["sets"].append({"set": name, "want": want, "you": text, "kind": measure.kind_of(want, r), "skill": r.get("skill") or "—"})
    return out


def run(root, real_md, to):
    """answers(root) in a process of its own → the JSON file to"""
    code = "import json, sys; sys.path.insert(0, %r); import gate; json.dump(gate.answers(%r, %r), open(%r, 'w'))" % (
        os.path.dirname(os.path.abspath(__file__)), root, real_md, to)
    return subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)


def compare(before, after):
    """→ {heading: [lines]}, and whether the gate fails"""
    found = {k: [] for k in ("NEW WRONG ACTION", "real turn no longer as it should", "look at each (real turns)",
                             "worse", "better", "changed", "new test sentences")}
    for b, a in zip(before["real"], after["real"]):
        if (b["outcome"], b["skill"]) == (a["outcome"], a["skill"]):
            continue
        line = "%s | %-40s %s %s → %s %s · %s" % (b["where"][:17], b["you"][:40], b["outcome"], b["skill"], a["outcome"], a["skill"], a["say"][:60])
        if b["met"] and a["met"] is False:
            found["real turn no longer as it should"].append(line)
        elif b["met"] is False and a["met"]:
            found["better"].append(line)
        elif a["outcome"] in ("act", "approve") and (a["skill"] != b["skill"] or b["outcome"] not in ("act", "approve")):
            found["look at each (real turns)"].append(line)
        elif b["outcome"] in ("act", "approve"):
            found["worse"].append(line)
        else:
            found["changed"].append(line)
    # a test sentence is matched by its set and words, not its place: a skill added or removed moves the others
    key = lambda s: (s["set"], s["want"], s["you"])
    was = {key(b): b for b in before["sets"]}
    found["new test sentences"] = ["%-11s %-18s %s → %s %s" % (a["set"], a["want"], a["you"][:60], a["kind"], a["skill"])
                                   for a in after["sets"] if key(a) not in was]
    found["NEW WRONG ACTION"] += [l for l in found["new test sentences"] if " → WRONG " in l]
    for a in after["sets"]:
        b = was.get(key(a))
        if b is None or (b["kind"], b["skill"]) == (a["kind"], a["skill"]):
            continue
        rank = RANK_NONE if b["want"] == "none" else RANK
        line = "%-11s %-18s %-60s %s %s → %s %s" % (b["set"], b["want"], b["you"][:60], b["kind"], b["skill"], a["kind"], a["skill"])
        if a["kind"] == "WRONG" and b["kind"] != "WRONG":
            found["NEW WRONG ACTION"].append(line)
        elif rank[a["kind"]] < rank[b["kind"]]:
            found["worse"].append(line)
        elif rank[a["kind"]] > rank[b["kind"]]:
            found["better"].append(line)
        else:
            found["changed"].append(line)
    return found, bool(found["NEW WRONG ACTION"] or found["real turn no longer as it should"])


def totals(answers_):
    count = lambda xs, k: sum(1 for x in xs if x == k)
    kinds = [s["kind"] for s in answers_["sets"]]
    outcomes = [r["outcome"] for r in answers_["real"]]
    return ("test sets: %d acted, %d asked first, %d not understood, %d wrong skill asked, %d WRONG; real turns: %d act, %d approve, %d ask, %d abstain"
            % tuple([count(kinds, k) for k in ("acted", "asked", "abstain", "wrong?", "WRONG")] +
                    [count(outcomes, k) for k in ("act", "approve", "ask", "abstain")]))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    ref = args[0] if args else "HEAD"
    sha = subprocess.run(["git", "rev-parse", "--short", ref], cwd=HERE, capture_output=True, text=True, check=True).stdout.strip()
    tmp = tempfile.mkdtemp(prefix="termnl-gate-")
    copy = os.path.join(tmp, "before")
    subprocess.run(["git", "worktree", "add", "-q", "--detach", copy, sha], cwd=HERE, check=True)
    try:
        jobs = [run(copy, REAL, os.path.join(tmp, "before.json")), run(HERE, REAL, os.path.join(tmp, "after.json"))]
        for j in jobs:
            if j.wait():
                sys.exit("the gate could not run:\n" + j.stderr.read())
        before, after = (json.load(open(os.path.join(tmp, n + ".json"))) for n in ("before", "after"))
    finally:
        if "--keep" not in sys.argv:
            subprocess.run(["git", "worktree", "remove", "--force", copy], cwd=HERE)
            shutil.rmtree(tmp, ignore_errors=True)
    found, failed = compare(before, after)
    print("The working copy against %s: %d real turns, %d test sentences" % (sha, len(after["real"]), len(after["sets"])))
    for heading, lines in found.items():
        if lines:
            print("\n%s (%d)" % (heading, len(lines)))
            for l in lines:
                print("  " + l)
    print("\nbefore: " + totals(before) + "\nafter:  " + totals(after))
    print("\n" + ("FAIL: a new wrong action, or a real turn no longer as it should" if failed else "PASS: no new wrong action"))
    sys.exit(1 if failed else 0)
