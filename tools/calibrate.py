"""python3 -m tools.calibrate [--independent] [--write] — RESEARCH.md, method B: where TermNL's two lines
should sit for the model as it is trained now, measured instead of chosen by hand.

TermNL acts when the model is sure enough of a skill and asks when it is less sure (agent.py, SURE and MAYBE).
Here the lines come from sentences the model did not learn from: the "Also said" lines of every skill are
cut into 5 parts; the model is trained 5 times, each time without one part, and reads that part. Then:

  the ask line   the lowest score the right skill gets, leaving out the lowest 5%: above it, 95 requests
                 in 100 get at least a question about the right skill (conformal prediction, CICC 2024)
  the act line   the lowest score where the skill read is wrong in at most 1 sentence in 100

--independent trains each label on its own (method G). --write stores the lines in model.json as
"lines", which agent.py uses instead of its own. No test set is read: they stay judges.
Needs numpy, like training."""
import json
import math
import os
import sys
import zlib

from termnl.examples import examples
from termnl.load import language_dir, load_language, read
from termnl.model import classify, train_classifier

FOLDS, MISS, WRONG = 5, 0.05, 0.01


def fold_of(skill, text):
    return zlib.crc32((skill + "|" + text).encode()) % FOLDS


def main():
    independent = "--independent" in sys.argv
    lang = load_language("en")
    skills, lists = lang["skills"], lang["lists"]
    none = [l[2:].strip() for l in read(os.path.join(language_dir("en"), "out-of-scope.md")).split("\n") if l.startswith("- ")]
    none_ex = [t for t in none for _ in range(2)]
    rows = []
    for k in range(FOLDS):
        kept = [{**s, "also": [t for t in s["also"] if fold_of(s["id"], t) != k]} for s in skills]
        held = [(s, t) for s in skills for t in s["also"] if fold_of(s["id"], t) == k]
        exs = examples(kept, lists)
        action = train_classifier([{"text": e["text"], "label": e["action"]} for e in exs] + [{"text": t, "label": "none"} for t in none_ex], independent=independent)
        obj = train_classifier([{"text": e["text"], "label": e["object"]} for e in exs] + [{"text": t, "label": "none"} for t in none_ex], independent=independent)
        for s, t in held:
            pa = {x["label"]: x["p"] for x in classify(action, t)}
            po = {x["label"]: x["p"] for x in classify(obj, t)}
            scored = sorted(((pa.get(o["action"], 0) * po.get(o["object"], 0), o["id"]) for o in skills), reverse=True)
            rows.append({"skill": s["id"], "text": t, "top": scored[0][1], "p top": scored[0][0],
                         "p right": next(p for p, i in scored if i == s["id"])})
        print("part %d of %d: %d sentences read" % (k + 1, FOLDS, len(held)), file=sys.stderr)

    n = len(rows)
    right = sorted(r["p right"] for r in rows)
    maybe = right[max(0, math.floor(MISS * (n + 1)) - 1)]
    tops = sorted(rows, key=lambda r: -r["p top"])
    sure, wrong = 1.0, 0
    for i, r in enumerate(tops):  # the lowest line that keeps the wrong readings above it at 1% at most
        wrong += r["top"] != r["skill"]
        if wrong <= WRONG * (i + 1):
            sure = r["p top"]
    lines = {"sure": round(sure, 3), "maybe": round(maybe, 3)}
    first = sum(r["top"] == r["skill"] for r in rows)
    print(json.dumps({"model": "independent" if independent else "shared", "sentences": n, "right skill first": first,
                      "lines": lines, "acted above the act line": sum(r["p top"] >= sure for r in rows),
                      "right skill at least asked": sum(r["p right"] >= maybe for r in rows)}, indent=1))
    if "--write" in sys.argv:
        path = os.path.join(language_dir("en"), "model.json")
        with open(path, encoding="utf-8") as f:
            m = json.load(f)
        m["lines"] = lines
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(m, separators=(",", ":")))
        print("lines written to " + os.path.relpath(path), file=sys.stderr)


if __name__ == "__main__":
    main()
