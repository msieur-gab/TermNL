"""python3 -m tools.why "sentence" [more…] — how TermNL reads a sentence: the words after cleaning and
correction, its shape, what the funnel names, the templates that read it, the model's action and object."""
import sys

from termnl.agent import Agent
from termnl.load import load_language
from tests.device import device


def why(agent, text):
    r = agent.reader
    toks = r.clean(text)
    fixed, fixes = r.correct(toks)
    print("\n" + text)
    print("  words:   " + " ".join(t["word"] for t in toks) + ("   (corrected: %s)" % ", ".join("%s→%s" % tuple(f) for f in fixes) if fixes else ""))
    for label, ts in (("typed", toks), ("corrected", fixed)) if fixes else (("typed", toks),):
        shape = r.shape(ts)
        acts, objs = r.names(shape)
        print("  %s: shape %s; names %s / %s" % (label, sorted(shape), sorted(acts) or "-", sorted(objs) or "-"))
        u = r.by_template(text, ts, shape)
        if u and u["how"] == "choose":
            print("    templates: " + " | ".join(o["skill"]["id"] for o in u["options"]))
        elif u:
            print("    template:  %s %s" % (u["skill"]["id"], {k: v.get("label") or v.get("text") for k, v in u["vals"].items()}))
        else:
            print("    template:  none")
        if r.model:
            from termnl.model import classify
            ws = [t["word"] for t in ts]
            pa, po = classify(r.model["action"], text, ws)[:3], classify(r.model["object"], text, ws)[:3]
            print("    model:     action %s; object %s" % (", ".join("%s %.2f" % (x["label"], x["p"]) for x in pa), ", ".join("%s %.2f" % (x["label"], x["p"]) for x in po)))
    out = agent.hear(text)
    agent.pending = None
    print("  → %s %s (%s %s) %s %s" % (out["outcome"], out.get("skill"), out.get("how"), out.get("p"), out.get("say"), out.get("chips") or ""))


if __name__ == "__main__":
    lang = load_language()
    agent = Agent(**lang, settings={"admin mode": "on"}, device=device, random=lambda: 0)
    for text in sys.argv[1:]:
        why(agent, text)
