"""python3 -m tests.real [-v] [--add] — the conversations people really had, against today's TermNL.

tests/real.md holds them (kept out of git, like logs/): each turn, what was typed, what TermNL did
then, and what it should do. "should (Claude):" is Claude's guess, for the person to confirm (remove
"(Claude)") or correct; "should:" alone is theirs.

    --add   adds the conversations in logs/ that real.md doesn't have yet, without a "should"
    -v      every turn, not only those that differ

How "should" is written: the outcome (act, ask, approve, abstain), then the skill if it matters, then
words in quotes that the command, or else the reply, must hold: act create-folder "Pictures".

The replay runs every conversation in order, in one throwaway home that starts as real.md's "Home at
the start" says. Only what can't harm runs there (making, renaming and listing files and folders, and
reading the device); opening, closing, restarting and switching things are simulated."""
import datetime
import glob
import json
import os
import random
import re
import shutil
import sys
import tempfile

from termnl.load import ROOT
from termnl.server import TermNL

HERE = os.path.join(ROOT, "tests", "real.md")
SAFE = ("create-", "rename-", "check-", "show-", "leave-folder", "open-folder")
OUTCOMES = ("act", "ask", "approve", "abstain")
GAP = 10 * 60  # a pause this long starts a new conversation


class Replay(TermNL):
    """TermNL in a throwaway home: nothing logged, the same reply every time, only harmless commands run"""
    def __init__(self, home):
        super().__init__(home=home)
        self.settings = {"admin mode": "on", "show commands": "on"}

    def agent(self, session):
        if session not in self.sessions:
            self.sessions[session] = self.Agent(**self.lang, settings=self.settings, device=self.device, random=lambda: 0)
        return self.sessions[session]

    def simulated(self, skill_id):
        return not skill_id.startswith(SAFE)

    def log(self, *args, **kwargs):
        pass


def parse(text):
    """→ (home at the start, [conversation: {title, turns: [{you, then, should, by}]}])"""
    home, conversations = [], []
    for line in text.split("\n"):
        if line.startswith("Home at the start:"):
            home = [p.strip() for p in line.split(":", 1)[1].split(",") if p.strip()]
        elif line.startswith("## "):
            conversations.append({"title": line[3:].strip(), "turns": []})
        elif line.startswith("- you: ") and conversations:
            conversations[-1]["turns"].append({"you": line[7:]})
        elif conversations and conversations[-1]["turns"]:
            m = re.match(r"^\s+- (then|should|should \(Claude\)): (.*)$", line)
            if m:
                turn = conversations[-1]["turns"][-1]
                key = "then" if m.group(1) == "then" else "should"
                turn[key] = m.group(2).strip()
                if key == "should":
                    turn["by"] = "Claude" if "Claude" in m.group(1) else "person"
    return home, conversations


def expected(should):
    """'act create-folder "Pictures"' → ("act", "create-folder", ["Pictures"])"""
    words = re.findall(r"[“\"]([^”\"]+)[”\"]", should)
    parts = re.sub(r"[“\"][^”\"]*[”\"]", "", should).split()
    outcome = parts[0] if parts and parts[0] in OUTCOMES else None
    skill = parts[1] if len(parts) > 1 and outcome else None
    return outcome, skill, words


def judge(should, r):
    """→ None when the reply is what should happen, else what differs"""
    outcome, skill, words = expected(should)
    if outcome is None:
        return "can't read the should: %s" % should
    if r["outcome"] != outcome:
        return "%s, not %s" % (r["outcome"], outcome)
    if skill and r.get("skill") != skill:
        return "%s, not %s" % (r.get("skill") or "no skill", skill)
    where = r.get("show") or r.get("say") or ""
    missing = [w for w in words if w not in where]
    return "without %s" % ", ".join("“%s”" % w for w in missing) if missing else None


def replay(verbose=False):
    """→ {"person": [as said, judged], "Claude": [...], "not judged": n}"""
    with open(HERE, encoding="utf-8") as f:
        start, conversations = parse(f.read())
    tally = {"person": [0, 0], "Claude": [0, 0], "not judged": 0}
    home = tempfile.mkdtemp(prefix="termnl-real-")
    try:
        for p in start:
            path = os.path.join(home, p.rstrip("/"))
            if p.endswith("/"):
                os.makedirs(path, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                open(path, "a").close()
        app = Replay(home)
        random.seed(0)
        for n, c in enumerate(conversations):
            if verbose:
                print("\n## %s" % c["title"])
            for t in c["turns"]:
                r = app.say(t["you"], "conversation %d" % n)
                now = "%s %s · %s" % (r["outcome"], r.get("skill") or "", (r.get("say") or "").replace("\n", " ")[:90])
                if "should" not in t:
                    tally["not judged"] += 1
                    if verbose:
                        print("  ?     %-40s %s" % (t["you"][:40], now))
                    continue
                tally[t["by"]][1] += 1
                wrong = judge(t["should"], r)
                if not wrong:
                    tally[t["by"]][0] += 1
                if wrong or verbose:
                    print("  %-5s %-40s %s%s" % ("ok" if not wrong else "DIFF", t["you"][:40], now,
                                                 "" if not wrong else "\n        should (%s): %s → %s" % (t["by"], t["should"], wrong)))
    finally:
        shutil.rmtree(home, ignore_errors=True)
    return tally


def summary(tally):
    p, c = tally["person"], tally["Claude"]
    return ("Real conversations: %d of %d turns as the person said, %d of %d as Claude guessed, %d not judged yet"
            % (p[0], p[1], c[0], c[1], tally["not judged"]))


def is_person(session):
    """the chat page names a conversation with a random id; tests name theirs by hand (claude-…, check-…)"""
    return re.match(r"^[0-9a-f]{8}$", session) is not None


def add():
    """appends the conversations of logs/ that real.md doesn't hold yet"""
    have = open(HERE, encoding="utf-8").read() if os.path.exists(HERE) else \
        "# Real conversations\n\nWhat people typed in the chat (logs/), kept out of git. See tests/real.py.\n\nHome at the start:\n"
    turns = []
    for f in sorted(glob.glob(os.path.join(ROOT, "logs", "*.jsonl"))):
        with open(f, encoding="utf-8") as lines:
            turns += [d for d in map(json.loads, lines) if is_person(d["session"])]
    turns.sort(key=lambda d: d["at"])
    conversations, last = [], {}
    for d in turns:
        at = datetime.datetime.fromisoformat(d["at"])
        before = last.get(d["session"])
        if before is None or (at - before[0]).total_seconds() > GAP:
            conversations.append([])
            before = (at, conversations[-1])
        before[1].append(d)
        last[d["session"]] = (at, before[1])
    added = 0
    for c in conversations:
        title = "%s, %s (%s)" % (c[0]["at"][:10], c[0]["at"][11:16], c[0]["session"])
        if "## " + title in have:
            continue
        have += "\n## %s\n\n" % title
        for d in c:
            then = "%s %s · %s" % (d["outcome"], d.get("skill") or "", (d.get("say") or "").replace("\n", " ")[:100])
            have += "- you: %s\n  - then: %s\n" % (d["text"], re.sub(r"\s+", " ", then).strip())
        added += 1
    with open(HERE, "w", encoding="utf-8") as f:
        f.write(have)
    print("%d conversations added to tests/real.md" % added)


if __name__ == "__main__":
    if "--add" in sys.argv:
        add()
    elif not os.path.exists(HERE):
        print("No tests/real.md yet: python3 -m tests.real --add")
    else:
        print(summary(replay("-v" in sys.argv)))
