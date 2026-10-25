"""Training sentences made from the skills' own templates: each template becomes many sentences,
with its optional words in and out, each alternative, each word for its action and object, and
sample values. Authors write a few readable lines; the model learns from all their variations."""
import zlib

from .text import words


def samples_for(kind, lists):
    """sample values for training only (words/samples.md); real values come from the device at run time"""
    if kind == "filetype":
        return [" ".join(p) for t in lists["filetypes"] for p in t["phrases"]]
    return lists["samples"].get(kind) or lists["samples"]["text"]


# of a skill's sentences, those said with the words it says mean its action (## Words, →). 0: none, the agent's
# rule reads them instead (agent.in_context). Tried 25 Oct 2026, not kept: VERB-WITH-OBJECT.md
MEANS_SHARE = 0


def walk(nodes, lists, skill, rnd):
    """one random walk through a template"""
    out = []
    for n in nodes:
        if n["t"] == "w":
            out.append(n["w"])
        elif n["t"] == "ref":
            ph = lists["refs"][n["name"]]
            if n["name"] == skill["action"]:  # what the skill says its words mean with its object (## Words): learned,
                # in a share of its sentences only, so its own words stay its strongest ("shut down" before "turn off")
                means = [p for objects, phrases, _ in skill.get("means", []) if not objects or skill["object"] in objects for p in phrases]
                if means and MEANS_SHARE and rnd() < MEANS_SHARE:
                    ph = means
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


def examples(skills, lists, per_skill=160, per_template=None, seed=7):
    """→ [{text, skill, action, object}], deduplicated. Each skill gets the same number of walks
    (per_skill), shared among its sentences, at least 10 each: a skill written as many short sentences
    weighs no more than one written as a few long ones (24 Oct 2026: written plainly, show process went
    from 5 templates to 16 sentences). per_template, when given, is the walks per sentence instead."""
    seen, out = set(), []
    for skill in skills:
        # each skill its own random stream, from its name: a skill dropped in leaves the sentences of every
        # other skill as they were (25 Oct 2026: one stream for all, adding check-kernel redrew every skill
        # after it in the alphabet, and their readings moved)
        rnd = rng(seed ^ zlib.crc32(skill["id"].encode("utf-8")))
        n = per_template or max(10, -(-per_skill // max(1, len(skill["compiled"]))))
        for nodes in skill["compiled"]:
            for _ in range(n):
                text = walk(nodes, lists, skill, rnd)
                key = skill["id"] + "|" + text
                if key in seen:
                    continue
                seen.add(key)
                out.append({"text": text, "skill": skill["id"], "action": skill["action"], "object": skill["object"]})
        # what people really say (## Also said), each counted three times: a few plain sentences among the
        # templates' many variations
        for text in skill["also"]:
            out += [{"text": text, "skill": skill["id"], "action": skill["action"], "object": skill["object"]}] * 3
    return out


def taught_words(exs):
    """The words a skill has been taught: every word of its generated sentences."""
    by = {}
    for e in exs:
        by.setdefault(e["skill"], set()).update(words(e["text"]))
    return by
