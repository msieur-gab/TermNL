"""Loads a language (its words and skills) and the device's settings, from disk. Nothing is trained: a skill
folder dropped in is read the next time the language is loaded ("learn what I taught you").

    termnl/languages/<lang>/words/      actions, objects, filetypes, conversation, samples, readings (.md)
    termnl/languages/<lang>/skills/     one folder per skill, a skill.md in each"""
import os
import time

from .skills import load
from .text import read_pairs

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # the project: settings.md, web/, logs/, tests/
LANGUAGES = os.path.join(HERE, "languages")


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
    out["read"] = int(time.time())  # when the skill files were last read ("are you learning?", readers.py)
    return out


def load_settings(root=ROOT):
    return read_pairs(read(os.path.join(root, "settings.md")))
