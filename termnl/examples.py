"""Training sentences made from the skills' own templates: each template becomes many sentences,
with its optional words in and out, each alternative, each word for its action and object, and
sample values. Authors write a few readable lines; the model learns from all their variations."""
from .text import words


def samples_for(kind, lists):
    """sample values for training only (words/samples.md); real values come from the device at run time"""
    if kind == "filetype":
        return [" ".join(p) for t in lists["filetypes"] for p in t["phrases"]]
    return lists["samples"].get(kind) or lists["samples"]["text"]


def walk(nodes, lists, skill, rnd):
    """one random walk through a template"""
    out = []
    for n in nodes:
        if n["t"] == "w":
            out.append(n["w"])
        elif n["t"] == "ref":
            ph = lists["refs"][n["name"]]
            out.append(" ".join(ph[int(rnd() * len(ph))]))
        elif n["t"] == "slot":
            s = samples_for(skill["values"][n["name"]]["kind"], lists)
            out.append(s[int(rnd() * len(s))])
        elif n["t"] == "alt":
            if n["opt"] and rnd() < 0.5:
                continue
            out.append(walk(n["alts"][int(rnd() * len(n["alts"]))], lists, skill, rnd))
    return " ".join(w for w in out if w)


def rng(seed=7):
    s = seed & 0xFFFFFFFF

    def r():
        nonlocal s
        s = (s * 1664525 + 1013904223) & 0xFFFFFFFF
        return s / 4294967296
    return r


def examples(skills, lists, per_template=40, seed=7):
    """→ [{text, skill, action, object}], deduplicated"""
    rnd = rng(seed)
    seen, out = set(), []
    for skill in skills:
        for nodes in skill["compiled"]:
            for _ in range(per_template):
                text = walk(nodes, lists, skill, rnd)
                key = skill["id"] + "|" + text
                if key in seen:
                    continue
                seen.add(key)
                out.append({"text": text, "skill": skill["id"], "action": skill["action"], "object": skill["object"]})
    return out


def taught_words(exs):
    """The words a skill has been taught: every word of its generated sentences."""
    by = {}
    for e in exs:
        by.setdefault(e["skill"], set()).update(words(e["text"]))
    return by
