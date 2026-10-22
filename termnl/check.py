"""python3 -m termnl.check [lang] — stops with each skill file's problem, or says how many skills are fine."""
import sys

from .load import load_language

lang = sys.argv[1] if len(sys.argv) > 1 else "en"
loaded = load_language(lang)
if loaded["errors"]:
    print("\n".join(loaded["errors"]), file=sys.stderr)
    sys.exit(1)
print("%d skills in %s, no problems." % (len(loaded["skills"]), lang))
