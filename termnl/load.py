"""Loads a language (its words, skills and model) and the device's settings, from disk.

    termnl/languages/<lang>/words/      actions, objects, filetypes, conversation, samples, readings (.md)
    termnl/languages/<lang>/skills/     one folder per skill, a skill.md in each
    termnl/languages/<lang>/model.json  trained from the above (python3 -m termnl.train)"""
import json
import os

from .skills import load
from .text import read_pairs

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # the project: settings.md, web/, logs/, tests/
LANGUAGES = os.path.join(HERE, "languages")
# what is the person's own (settings.md, logs/, a model trained again on the device): the project itself unless
# TERMNL_DATA names a folder of its own, so the program can be installed read-only (SymbiOS: ~/.config/termnl)
DATA = os.path.abspath(os.path.expanduser(os.environ.get("TERMNL_DATA") or ROOT))


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def language_dir(lang="en", languages=LANGUAGES):
    return os.path.join(languages, lang)


def load_language(lang="en", languages=LANGUAGES):
    d = language_dir(lang, languages)
    lists = {k: read(os.path.join(d, "words", k + ".md")) for k in ("actions", "objects", "filetypes", "conversation", "samples", "readings")}
    if os.path.exists(os.path.join(d, "words", "values.md")):  # how ## What it needs is written (plain.py)
        lists["values"] = read(os.path.join(d, "words", "values.md"))
    skills = {}
    for id in sorted(os.listdir(os.path.join(d, "skills"))):
        f = os.path.join(d, "skills", id, "skill.md")
        if os.path.exists(f):
            skills[id] = read(f)
    out = load(lists, skills)
    m = model_path(lang, languages)
    if os.path.exists(m):
        out["model"] = json.loads(read(m))
    return out


def model_dir(lang="en", languages=LANGUAGES):
    """where the model trained on this device is kept: beside the skills, or in the data folder when it has its own"""
    return language_dir(lang, languages) if DATA == ROOT or languages != LANGUAGES else os.path.join(DATA, "languages", lang)


def model_path(lang="en", languages=LANGUAGES):
    """the model trained on this device if there is one, else the one that came with the program"""
    m = os.path.join(model_dir(lang, languages), "model.json")
    return m if os.path.exists(m) else os.path.join(language_dir(lang, languages), "model.json")


def load_settings(root=DATA):
    """settings.md from the data folder; a new data folder starts from the program's own"""
    path = os.path.join(root, "settings.md")
    if not os.path.exists(path) and root != ROOT:
        os.makedirs(root, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(read(os.path.join(ROOT, "settings.md")))
    return read_pairs(read(path))
