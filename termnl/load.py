"""Loads a language's lists, skills and model, and the device's settings, from disk."""
import json
import os

from .skills import load
from .text import read_pairs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def load_language(lang="en", root=ROOT):
    d = os.path.join(root, lang)
    lists = {k: read(os.path.join(d, k + ".md")) for k in ("actions", "objects", "filetypes", "answers")}
    skills = {}
    for id in sorted(os.listdir(os.path.join(d, "skills"))):
        f = os.path.join(d, "skills", id, "skill.md")
        if os.path.exists(f):
            skills[id] = read(f)
    out = load(lists, skills)
    m = os.path.join(root, "model", lang + ".json")
    if os.path.exists(m):
        out["model"] = json.loads(read(m))
    return out


def load_settings(root=ROOT):
    return read_pairs(read(os.path.join(root, "settings.md")))
