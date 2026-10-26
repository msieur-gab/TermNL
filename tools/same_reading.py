"""python3 -m tools.same_reading save|check — do the skill files still read the same sentences?

save: before a rewrite of the skill files (tools/to_plain.py), records how every sentence is read: the
sentences the templates themselves generate (200 per template), every test set and every Also said line.
check: after it, with the same model, reads them again and lists each difference (skill, outcome, values).
The model is not retrained in between, so a difference can only come from the sentences' new form."""
import json
import os
import re
import sys

from termnl.agent import Agent
from termnl.examples import examples
from termnl.load import ROOT, load_language
from tests.device import device

SAVED = os.path.join(ROOT, "tools", ".same_reading.json")


def corpus(lang):
    texts = {e["text"] for e in examples(lang["skills"], lang["lists"], per_template=200, seed=11)}
    for name in ("phrasings", "probes", "heldout", "blind"):
        with open(os.path.join(ROOT, "tests", name + ".md"), encoding="utf-8") as f:
            texts |= {m.group(1) for m in (re.match(r"^- [\w-]+: (.+)$", l) for l in f) if m}
    return sorted(texts)


def readings(lang, texts):
    out = {}
    for t in texts:
        r = Agent(**lang, settings={"admin mode": "on"}, device=device, random=lambda: 0).hear(t)
        out[t] = [r["outcome"], r.get("skill"), r.get("command"), r.get("args"), r["say"]]
    return out


if __name__ == "__main__":
    lang = load_language("en")
    if sys.argv[1:] == ["save"]:
        texts = corpus(lang)
        json.dump({"texts": texts, "readings": readings(lang, texts)}, open(SAVED, "w"))
        print("%d sentences saved" % len(texts))
    else:
        saved = json.load(open(SAVED))
        now = readings(lang, saved["texts"])
        diff = [t for t in saved["texts"] if now[t] != saved["readings"][t]]
        for t in diff:
            print("%r\n  before: %s\n  now:    %s" % (t, saved["readings"][t][:3], now[t][:3]))
        print("%d sentences read again, %d differ" % (len(saved["texts"]), len(diff)))
