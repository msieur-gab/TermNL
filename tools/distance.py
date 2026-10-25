"""python3 -m tools.distance — RESEARCH.md, method A: is a sentence the model guesses at far from every taught
sentence when it is out of scope, and near when it is a real request? Tested 25 Oct 2026: no (RESEARCH.md).

For every test sentence read by the model (not by a template), the words it was read with (typos corrected,
values left out) are compared with every sentence TermNL trains on, with the model's own clues and weights:
  nn    the closest taught sentence, any skill        skn   the closest taught sentence of the skill guessed
  cen   the average of the guessed skill's sentences  cov   the share of its words that were taught
each on all clues, on words and word pairs only, and on words only. Then, for each measure, how many
out-of-scope sentences a line would refuse, and at what cost: the requests it would lose (handled or asked
first today) and the wrong readings it would refuse. Standard library only."""
import math
from collections import defaultdict

from termnl.agent import Agent
from termnl.examples import examples
from termnl.load import load_language
from termnl.model import features
from termnl.text import words
from tests.device import device
from tests.measure import SETS, kind_of, lines_of

CLUES = {"all": lambda f: True, "words": lambda f: f[:2] in ("w:", "b:"), "w": lambda f: f[:2] == "w:"}


def main():
    lang = load_language("en")
    model = lang["model"]
    idf = {f: row[0] for part in ("action", "object") for f, row in model[part]["weights"].items()}
    rare = max(idf.values())  # a clue the model never kept weighs as the rarest it kept
    taught = {w for ws in model["taught"].values() for w in ws}

    def vec(ws, keep):
        c = defaultdict(int)
        for f in features(None, ws):
            if keep(f):
                c[f] += 1
        v = {f: (1 + math.log(n)) * idf.get(f, rare) for f, n in c.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1
        return {f: x / norm for f, x in v.items()}

    def cos(a, b):
        a, b = (a, b) if len(a) <= len(b) else (b, a)
        return sum(x * b.get(f, 0) for f, x in a.items())

    skill_of = {(s["action"], s["object"]): s["id"] for s in lang["skills"]}
    train = {k: defaultdict(list) for k in CLUES}
    for e in examples(lang["skills"], lang["lists"]):
        for k, keep in CLUES.items():
            train[k][skill_of[(e["action"], e["object"])]].append(vec(words(e["text"]), keep))
    cent = {k: {} for k in CLUES}
    for k in CLUES:
        for s, vs in train[k].items():
            c = defaultdict(float)
            for v in vs:
                for f, x in v.items():
                    c[f] += x
            n = math.sqrt(sum(x * x for x in c.values())) or 1
            cent[k][s] = {f: x / n for f, x in c.items()}

    last, understand = {}, Agent.understand

    def spy(self, text, toks):
        last["u"] = understand(self, text, toks)
        return last["u"]

    Agent.understand = spy
    rows = []
    for name in SETS:
        for want, text in lines_of(name):
            last.clear()
            r = Agent(**lang, settings={"admin mode": "on"}, device=device, random=lambda: 0).hear(text)
            u = last.get("u")
            if not u or u["how"] != "model":
                continue
            values = {w for v in u["vals"].values() for w in words(v.get("text") or "")}
            ws = [t["word"] for t in u["toks"] if t["word"] not in values]
            row = {"oos": want == "none", "kind": kind_of(want, r), "text": text, "p": u["p"],
                   "cov": sum(w in taught for w in ws) / max(1, len(ws))}
            sid = u["skill"]["id"]
            for k, keep in CLUES.items():
                q = vec(ws, keep)
                row["nn " + k] = max(cos(q, v) for vs in train[k].values() for v in vs)
                row["skn " + k] = max(cos(q, v) for v in train[k][sid])
                row["cen " + k] = cos(q, cent[k][sid])
            rows.append(row)
    Agent.understand = understand

    oos = [r for r in rows if r["oos"]]
    good = [r for r in rows if not r["oos"] and r["kind"] in ("acted", "asked")]
    bad = [r for r in rows if not r["oos"] and r["kind"] not in ("acted", "asked")]
    print("%d sentences read by the model: %d out of scope, %d requests handled or asked first, %d wrong readings\n"
          % (len(rows), len(oos), len(good), len(bad)))
    for m in [k for k in rows[0] if k not in ("oos", "kind", "text")]:
        print(m)
        for t in sorted({r[m] for r in oos}):
            lost = sum(r[m] <= t for r in good)
            if lost <= 4:
                print("   under %.3f: %d of %d out of scope refused, %d requests lost, %d wrong readings refused"
                      % (t + 0.0005, sum(r[m] <= t for r in oos), len(oos), lost, sum(r[m] <= t for r in bad)))
    print("\nthe farthest, closest taught sentence (nn all):")
    for r in sorted(rows, key=lambda r: r["nn all"])[:12]:
        print("   %.2f  %-3s %-7s %s" % (r["nn all"], "OOS" if r["oos"] else "", r["kind"], r["text"]))


if __name__ == "__main__":
    main()
