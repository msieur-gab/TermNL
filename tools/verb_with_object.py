"""python3 tools/verb_with_object.py MODEL.json [rules=off] [opposites=off] [joins=off] — the six test sets with a
given model, with the agent's rules for words in their context turned off (VERB-WITH-OBJECT.md, 25 Oct 2026).

  rules=off      no "meaning with an object" rewrite ("turn on the music" → play): the model must know it
  opposites=off  "turn the board on" may be offered its opposite
  joins=off      split verbs not joined ("turn the music off")

Prints the counts; writes every sentence's answer next to the model (MODEL.json.<options>.lines). A model to try:
  python3 -c "import json, termnl.model as M, termnl.examples as X; M.PAIRS = 2; X.MEANS_SHARE = 0.1;
  from termnl.train import train_language; json.dump(train_language('en')[0], open('pairs2.json', 'w'))"
"""
import json, sys, collections
sys.path.insert(0, ".")
import termnl.agent as A
from termnl.load import load_language
from tests import measure as M
from tests.device import device

model_path = sys.argv[1]
opts = dict(a.split("=") for a in sys.argv[2:])
lang = load_language("en")
lang["model"] = json.load(open(model_path))
if opts.get("opposites") == "off":
    lang["lists"]["opposites"] = {}
orig = A.Agent.in_context
if opts.get("rules") == "off":
    # no rewriting by "meaning with an object"; split verbs still joined unless joins=off
    def ic(self, toks):
        keep = self.lists["in_context"]
        self.lists["in_context"] = []
        try:
            out = orig(self, toks) if opts.get("joins", "on") == "on" else toks
        finally:
            self.lists["in_context"] = keep
        return out
    A.Agent.in_context = ic
elif opts.get("joins") == "off":
    raise SystemExit("joins=off only with rules=off")
tot = collections.Counter()
lines = []
for s in M.SETS:
    for want, text in M.lines_of(s):
        r = A.Agent(**lang, settings={"admin mode": "on"}, device=device, random=lambda: 0).hear(text)
        k = M.kind_of(want, r) + ("(oos)" if want == "none" else "")
        tot[k] += 1
        lines.append("%s\t%s\t%s\t%s\t%s" % (s, k, want, r.get("skill") or "—", text))
print(json.dumps(dict(sorted(tot.items()))))
open(model_path + "." + "_".join("%s-%s" % kv for kv in sorted(opts.items())) + ".lines", "w").write("\n".join(lines))
