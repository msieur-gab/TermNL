"""python3 -m tools.receipt — what a change moves, sentence by sentence, with the cause of each move.

    python3 -m tools.receipt                       every test sentence's answer today → data/receipt.json
    python3 -m tools.receipt --against before.json  the answers that moved since that file, each with its cause
    python3 -m tools.receipt --skills a b           trains without these skill folders, then with them:
                                                    what dropping them in moved (the model is retrained twice)

A move is a sentence whose outcome, skill or way of reading (template, model, frame) changed. Its cause is
read from the two answers: a typo read differently (TYPO), another path taken (ROUTE: template → model…),
the unknown words changed (UNKNOWN), the model's best pair changed (MODEL), or only its confidence moved
across a line (LINE). The sets are those of tests/measure.py; a code change is judged with the committed
model, a skill with a retrained one."""
import json
import os
import sys
import time

from termnl.agent import Agent
from termnl.examples import examples, taught_words
from termnl.load import LANGUAGES, ROOT, language_dir, load_language, read
from termnl.model import classify, train_classifier
from termnl.skills import load
from tests.device import device
from tests.measure import SETS, kind_of, lines_of

OUT = os.path.join(ROOT, "data", "receipt.json")


def answer(lang, model, want, text):
    """one sentence, heard by a fresh agent → the facts a move is read from"""
    a = Agent(lists=lang["lists"], skills=lang["skills"], model=model, settings={"admin mode": "on"}, device=device, random=lambda: 0)
    r = a.hear(text)
    top = None
    if model:
        ws = [t["word"] for t in a.clean(text)]
        pa, po = classify(model["action"], text, ws)[:3], classify(model["object"], text, ws)[:3]
        top = max(((x["label"], y["label"], round(x["p"] * y["p"], 3)) for x in pa for y in po), key=lambda t: t[2])
    return {"want": want, "text": text, "kind": kind_of(want, r), "outcome": r["outcome"], "skill": r.get("skill"), "how": r.get("how"),
            "p": r.get("p"), "unknown": r.get("unknown") or [], "fixes": r.get("corrections") or [], "model": top, "say": r["say"][:60]}


def answers(lang, model):
    return [answer(lang, model, want, text) for s in SETS for want, text in lines_of(s)]


def cause(a, b):
    c = []
    if a["fixes"] != b["fixes"]:
        c.append("TYPO %s → %s" % (a["fixes"] or "none", b["fixes"] or "none"))
    if a["how"] != b["how"]:
        c.append("ROUTE %s → %s" % (a["how"] or "nothing", b["how"] or "nothing"))
    if a["unknown"] != b["unknown"]:
        c.append("UNKNOWN %s → %s" % (a["unknown"] or "none", b["unknown"] or "none"))
    if a["model"] and b["model"]:
        if a["model"][:2] != b["model"][:2]:
            c.append("MODEL %s → %s" % (a["model"][:2], b["model"][:2]))
        elif abs(a["model"][2] - b["model"][2]) >= 0.02:
            c.append("LINE %.2f → %.2f" % (a["model"][2], b["model"][2]))
    return "; ".join(c) or "same reading, another answer"


def moved(before, after):
    out = []
    for a, b in zip(before, after):
        if a["text"] != b["text"]:
            continue  # a set changed: only the sentences both hold are compared
        if (a["kind"], a["skill"], a["how"]) != (b["kind"], b["skill"], b["how"]):
            out.append((a, b))
    return out


def say(pairs, n):
    worse = sum(1 for a, b in pairs if b["kind"] == "WRONG" and a["kind"] != "WRONG")
    print("%d of %d answers moved; %d into a wrong action" % (len(pairs), n, worse))
    for a, b in pairs:
        print("- %-16s %-44s %-8s %-18s → %-8s %-18s %s" % (a["want"], a["text"][:44], a["kind"], "%s(%s)" % (a["skill"] or "—", a["how"] or "—"),
                                                        b["kind"], "%s(%s)" % (b["skill"] or "—", b["how"] or "—"), cause(a, b)))


def train(lang):
    exs = examples(lang["skills"], lang["lists"])
    none = [l[2:].strip() for l in read(os.path.join(language_dir("en"), "out-of-scope.md")).split("\n") if l.startswith("- ")]
    none_ex = [t for t in none for _ in range(2)]
    t0 = time.time()
    m = {"action": train_classifier([{"text": e["text"], "label": e["action"]} for e in exs] + [{"text": t, "label": "none"} for t in none_ex]),
         "object": train_classifier([{"text": e["text"], "label": e["object"]} for e in exs] + [{"text": t, "label": "none"} for t in none_ex]),
         "taught": {k: sorted(s) for k, s in taught_words(exs).items()}}
    print("  trained on %d sentences, %d skills, %.0fs" % (len(exs), len(lang["skills"]), time.time() - t0))
    return m


def without(exclude):
    d = language_dir("en", LANGUAGES)
    lists = {k: read(os.path.join(d, "words", k + ".md")) for k in ("actions", "objects", "filetypes", "conversation", "samples", "readings", "values")}
    skills = {i: read(os.path.join(d, "skills", i, "skill.md")) for i in sorted(os.listdir(os.path.join(d, "skills"))) if i not in exclude}
    lang = load(lists, skills)
    if lang["errors"]:
        raise ValueError("\n".join(lang["errors"]))
    return lang


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--skills"]:
        dropped = set(args[1:])
        print("without %s:" % ", ".join(sorted(dropped)))
        a = without(dropped)
        before = [x for x in answers(a, train(a)) if x["want"] not in dropped]
        print("with them:")
        b = without(set())
        after = [x for x in answers(b, train(b)) if x["want"] not in dropped]
        say(moved(before, after), len(after))
    else:
        lang = load_language("en")
        now = answers(lang, lang.get("model"))
        if args[:1] == ["--against"]:
            with open(args[1], encoding="utf-8") as f:
                before = json.load(f)
            say(moved(before, now), len(now))
        else:
            os.makedirs(os.path.dirname(OUT), exist_ok=True)
            with open(OUT, "w", encoding="utf-8") as f:
                json.dump(now, f, ensure_ascii=False, indent=0)
            kinds = {}
            for x in now:
                kinds[x["kind"]] = kinds.get(x["kind"], 0) + 1
            print("%d answers → %s (%s)" % (len(now), os.path.relpath(OUT, ROOT), ", ".join("%s %d" % kv for kv in sorted(kinds.items()))))
