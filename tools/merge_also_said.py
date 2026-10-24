"""python3 -m tools.merge_also_said data/<file>.md [--dry] — adds proposed "Also said" sentences (a `## <skill>`
section per skill, `## none` for out-of-scope) to the skill files, after checking each one:

  dropped  the same words as a sentence of a test set (training on a test would make its score lie)
  dropped  already in a skill, or proposed for two skills (one sentence teaching two skills teaches neither)
  dropped  read by another skill's template (the template wins anyway; listed, as it may be a template's fault)
  dropped  for none: acted on by today's TermNL

Then retrain: python3 -m termnl.train"""
import os
import re
import sys

from termnl.agent import Agent
from termnl.load import ROOT, language_dir, load_language
from termnl.text import words
from tests.device import device


def norm(t):
    return " ".join(words(t))


def proposals(path):
    cur, out = None, {}
    with open(path, encoding="utf-8") as f:
        for l in f:
            m = re.match(r"^## (\S+)", l)
            if m:
                cur = m.group(1)
                out.setdefault(cur, [])
            elif l.startswith("- ") and cur:
                out[cur].append(l[2:].strip())
    return out


def tests():
    out = set()
    for name in os.listdir(os.path.join(ROOT, "tests")):
        if name.endswith(".md"):
            with open(os.path.join(ROOT, "tests", name), encoding="utf-8") as f:
                out |= {norm(m.group(1)) for m in (re.match(r"^- [\w-]+: (.+)$", l) for l in f) if m}
    return out


def review(prop, lang):
    held, existing = tests(), {norm(a) for s in lang["skills"] for a in s["also"]}
    ids = {s["id"] for s in lang["skills"]}
    seen = {}
    for sk, ss in prop.items():
        for t in ss:
            seen.setdefault(norm(t), set()).add(sk)
    keep, dropped = {}, {"same as a test sentence": [], "already in a skill": [], "proposed for two skills": [],
                         "read by another skill's template": [], "not a skill": []}
    for sk, ss in prop.items():
        for t in ss:
            n = norm(t)
            why = ("not a skill" if sk not in ids and sk != "none" else "same as a test sentence" if n in held else
                   "already in a skill" if n in existing else "proposed for two skills" if len(seen[n]) > 1 else None)
            if not why:
                r = Agent(**lang, settings={"admin mode": "on"}, device=device, random=lambda: 0).hear(t)
                if (r.get("how") == "template" and r.get("skill") != sk) or (sk == "none" and r["outcome"] in ("act", "approve")):
                    why = "read by another skill's template"
            if why:
                dropped[why].append((sk, t))
            else:
                keep.setdefault(sk, []).append(t)
    return keep, dropped


def merge(keep, source):
    base = language_dir("en")
    for sk, ss in keep.items():
        lines = "\n".join("- " + t for t in ss)
        if sk == "none":
            p = os.path.join(base, "out-of-scope.md")
            with open(p, encoding="utf-8") as f:
                s = f.read().rstrip("\n")
            s += "\n\nFrom %s:\n\n%s\n" % (source, lines)
        else:
            p = os.path.join(base, "skills", sk, "skill.md")
            with open(p, encoding="utf-8") as f:
                s = f.read()
            if "## Also said" in s:
                i = s.index("## Also said")
                j = s.find("\n## ", i + 5)
                j = len(s) if j < 0 else j
                s = s[:i] + s[i:j].rstrip("\n") + "\n" + lines + "\n\n" + s[j + 1:]
            else:
                j = next(s.index(h) for h in ("## What it needs", "## Values", "## Command", "## When") if h in s)
                s = s[:j] + "## Also said\n\n" + lines + "\n\n" + s[j:]
        with open(p, "w", encoding="utf-8") as f:
            f.write(s)


if __name__ == "__main__":
    path = [a for a in sys.argv[1:] if not a.startswith("-")][0]
    keep, dropped = review(proposals(path), load_language("en"))
    for why, items in dropped.items():
        if items:
            print("dropped, %s: %d" % (why, len(items)))
            for sk, t in items:
                print("   %-18s %s" % (sk, t))
    print("kept: %d" % sum(len(v) for v in keep.values()))
    if "--dry" not in sys.argv:
        merge(keep, os.path.relpath(path, ROOT))
