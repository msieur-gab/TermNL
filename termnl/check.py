"""python3 -m termnl.check [lang] — stops with each skill file's problem, or says how many skills are fine."""
import os
import sys

from .load import language_dir, load_language

lang = sys.argv[1] if len(sys.argv) > 1 else "en"
loaded = load_language(lang)
if loaded["errors"]:
    print("\n".join(loaded["errors"]), file=sys.stderr)
    sys.exit(1)
# each skill brings its own proof: a tests.md beside its skill.md, sentences people would say (python3 -m tests.measure skills)
FEW = 5
d = os.path.join(language_dir(lang), "skills")
thin = []
for id in sorted(s["id"] for s in loaded["skills"]):
    f = os.path.join(d, id, "tests.md")
    n = sum(1 for l in open(f, encoding="utf-8").read().split("\n") if l.startswith("- ")) if os.path.exists(f) else 0
    if n < FEW:
        thin.append("%s: %s" % (id, "no tests.md" if not os.path.exists(f) else "%d test sentence%s, fewer than %d" % (n, "" if n == 1 else "s", FEW)))
if thin:
    print("Skills with too few test sentences (a warning, not an error):\n  " + "\n  ".join(thin))
print("%d skills in %s, no problems." % (len(loaded["skills"]), lang))
