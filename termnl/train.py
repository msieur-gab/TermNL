"""python3 -m termnl.train [lang] — trains the tagger and the skill classifier from the skill files and the
out-of-scope examples, and writes languages/<lang>/model.json. Standard library only: it runs on the
board, in a minute or two, when the person says "learn what I taught you"."""
import json
import os
import sys
import time

from . import tagger
from .examples import ARTICLES, examples, taught_words
from .load import LANGUAGES, language_dir, load_language, read
from .model import features, train_classifier
from .text import words

NONE_TIMES = 2  # how many times each out-of-scope sentence counts (57 of them against 12,000 sentences of the skills)
KIND_OF_LIST = {"@sys.folder": "folder", "@sys.service": "service", "@sys.network": "network", "@sys.app": "app",
                "@sys.running": "running", "@sys.music": "music", "@sys.host": "host", "@sys.file": "file"}


def sample_lists(lists):
    """the samples as the lists a device would have (kind → words), for training; the device's own at run time"""
    out = {}
    for kind, samples in lists["samples"].items():
        if kind in KIND_OF_LIST:
            out[KIND_OF_LIST[kind]] = {w for s in samples for w in words(s)[1 if len(words(s)) > 1 and words(s)[0] in ARTICLES else 0:]}
    out["type"] = {w for t in lists["filetypes"] for ph in t["phrases"] for w in ph}
    return out


def context(lists, list_words, vocab):
    """what the tagger looks up (tagger.Context), from the shared lists and the lists given"""
    said = lists["conversation"]
    small = {w for ph in said.get("small words", []) for w in ph}
    leads = {ph[0] for ph in said.get("before a name", []) if len(ph) == 1}
    return tagger.Context(list_words, lists["refs"], small, leads, set(vocab))


def train_language(lang="en", languages=LANGUAGES, passes=(10, 8)):
    loaded = load_language(lang, languages)
    if loaded["errors"]:
        raise ValueError("\n".join(loaded["errors"]))
    lists, skills = loaded["lists"], loaded["skills"]
    exs = examples(skills, lists)
    none = [l[2:].strip() for l in read(os.path.join(language_dir(lang, languages), "out-of-scope.md")).split("\n") if l.startswith("- ")]
    # the words TermNL knows: those of the sentences themselves, never a sample value alone, so a value looks
    # to the tagger in training as a device's own names will at run time: a word it doesn't know
    vocab = sorted({w for e in exs for w, t in e["tagged"] if not t.startswith("V:")}
                   | {w for phs in lists["conversation"].values() for ph in phs for w in ph})  # and the conversation's own words ("now", "same for")
    ctx = context(lists, sample_lists(lists), vocab)
    t0 = time.time()
    tag_model = tagger.train([e["tagged"] for e in exs], ctx, passes=passes[0])
    # the out-of-scope sentences, tagged as the tagger reads them (nobody wrote their tags down), counted several times: there are few
    tagged_none = []
    for text in none:
        ws = words(text)
        tagged_none += [list(zip(ws, tagger.decode(tag_model["weights"], tag_model["tags"], ws, ctx)))] * NONE_TIMES
    rows = [{"features": features([w for w, _ in e["tagged"]], [t for _, t in e["tagged"]]), "label": e["skill"]} for e in exs]
    rows += [{"features": features([w for w, _ in t], [x for _, x in t]), "label": "none"} for t in tagged_none]
    skill_model = train_classifier(rows, passes=passes[1], rate=6.0, top=4)
    taught = {k: sorted(s) for k, s in taught_words(exs, skills, lists).items()}
    # when it was trained, read back by "are you learning?" (readers.py, learning)
    return {"lang": lang, "trained": int(time.time()), "tagger": tag_model, "vocab": vocab, "skill": skill_model, "taught": taught}, len(exs), time.time() - t0


if __name__ == "__main__":
    lang = sys.argv[1] if len(sys.argv) > 1 else "en"
    model, n, seconds = train_language(lang)
    out = json.dumps(model, separators=(",", ":"))
    # the model in use is replaced only once the new one is whole; the one before is kept beside it
    path = os.path.join(language_dir(lang), "model.json")
    with open(path + ".new", "w", encoding="utf-8") as f:
        f.write(out)
    if os.path.exists(path):
        os.replace(path, os.path.join(language_dir(lang), "model.previous.json"))
    os.replace(path + ".new", path)
    print("%d sentences, trained in %.1fs, %d KB → termnl/languages/%s/model.json" % (n, seconds, round(len(out) / 1024), lang))
