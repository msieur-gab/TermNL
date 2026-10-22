"""python3 -m termnl.train [lang] — trains the action and object models from the skill files and the
out-of-scope examples, and writes languages/<lang>/model.json."""
import json
import os
import sys
import time

from .examples import examples, taught_words
from .load import LANGUAGES, language_dir, load_language, read
from .model import train_classifier


def train_language(lang="en", languages=LANGUAGES):
    loaded = load_language(lang, languages)
    if loaded["errors"]:
        raise ValueError("\n".join(loaded["errors"]))
    exs = examples(loaded["skills"], loaded["lists"])
    none = [l[2:].strip() for l in read(os.path.join(language_dir(lang, languages), "out-of-scope.md")).split("\n") if l.startswith("- ")]
    none_ex = [t for t in none for _ in range(2)]  # counted twice: there are few of them
    t0 = time.time()
    action = train_classifier([{"text": e["text"], "label": e["action"]} for e in exs] + [{"text": t, "label": "none"} for t in none_ex])
    obj = train_classifier([{"text": e["text"], "label": e["object"]} for e in exs] + [{"text": t, "label": "none"} for t in none_ex])
    taught = {k: sorted(s) for k, s in taught_words(exs).items()}
    return {"lang": lang, "action": action, "object": obj, "taught": taught}, len(exs), time.time() - t0


if __name__ == "__main__":
    lang = sys.argv[1] if len(sys.argv) > 1 else "en"
    model, n, seconds = train_language(lang)
    out = json.dumps(model, separators=(",", ":"))
    with open(os.path.join(language_dir(lang), "model.json"), "w", encoding="utf-8") as f:
        f.write(out)
    print("%d sentences, trained in %.1fs, %d KB → termnl/languages/%s/model.json" % (n, seconds, round(len(out) / 1024), lang))
