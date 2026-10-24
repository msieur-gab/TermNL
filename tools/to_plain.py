"""python3 -m tools.to_plain [skill ...] — rewrites skill files from templates (## Sentences, ## Values) to
plain sentences (## People say, ## What it needs; termnl/plain.py). Every skill when none is named.

Each template becomes one or more plain sentences that read the same sentences: a choice between phrases
("(what is|what's)") becomes one sentence per phrase; a word that would now stand for a whole family of
words is kept in quotes. Check what changed with python3 -m tools.same_reading."""
import os
import re
import sys

from termnl.load import language_dir, load_language
from termnl.plain import phrases_of

KINDS = {("text", False): "a name", ("text", True): "a new name", ("secret", False): "a secret", ("filetype", False): "a file type",
         ("@sys.folder", False): "a folder on the device", ("@sys.file", False): "a file on the device",
         ("@sys.service", False): "a service on the device", ("@sys.app", False): "an app on the device",
         ("@sys.running", False): "a running app", ("@sys.music", False): "music on the device", ("@sys.network", False): "a network around"}


def plain_sentences(nodes, lists, own=()):
    """own: the skill's action and object. A word of theirs that a template wrote as a plain word ("reboot"
    in restart system) is let stand for its whole family, as an author would mean it, unless the sentence
    already says that family ("create a new folder": "new" is a word for create, so it stays "new")."""
    known = phrases_of(lists)
    mine = lambda w: any(f in own for f in known.get((w,), []))

    def word(w):
        return '"%s"' % w if (w,) in known else w

    def simple(alt):
        """one word that can sit in a / : a plain word, or an action or object of one word"""
        if len(alt) != 1:
            return None
        n = alt[0]
        if n["t"] == "w" and ((n["w"],) not in known or mine(n["w"])):
            return n["w"]
        if n["t"] == "ref":
            first = lists["refs"][n["name"]][0]
            return first[0] if len(first) == 1 else None
        return None

    def node(n):
        if n["t"] == "w":
            return [word(n["w"])]
        if n["t"] == "slot":
            return ["{%s}" % n["name"]]
        if n["t"] == "ref":
            return [" ".join(lists["refs"][n["name"]][0])]
        alts = n["alts"]
        words = [simple(a) for a in alts]
        if len(alts) > 1 and all(words):
            joined = "/".join(words)
            return ["(%s)" % joined] if n["opt"] else [joined]
        if n["opt"] and len(alts) == 1:
            inner = seq(alts[0])
            if len(inner) == 1:
                return ["(%s)" % inner[0]]
        out = [""] if n["opt"] else []
        for a in alts:
            out += seq(a)
        return out

    def seq(ns):
        variants = [""]
        for n in ns:
            variants = [(v + " " + o).strip() for v in variants for o in node(n)]
        return variants

    def unquote(s):
        said = set()
        for tok in re.findall(r'"[^"]*"|[^\s()/"{}]+', s):
            if not tok.startswith('"'):
                said |= set(known.get((tok,), []))
        for q in re.findall(r'"([^"]*)"', s):
            fam = set(known.get((q,), []))
            if fam & set(own) and not fam & said:
                s = s.replace('"%s"' % q, q, 1)
                said |= fam
        return s

    out = []
    for s in seq(nodes):
        s = unquote(re.sub(r"\s+", " ", s).strip())
        if s and s not in out:
            out.append(s)
    return out


def needs_line(name, v, replies):
    line = "- {%s}: %s." % (name, KINDS[(v["kind"], bool(v.get("new")))])
    d = v.get("default")
    if d:
        said = {"here": "where you are", "parent": "the folder above"}.get(d)
        if not said and d.startswith("parent of "):
            said = "the folder {%s} is in" % d[10:]
        line += " If it's not said: %s." % (said or d)
    elif v["required"]:
        line += " If it's missing, ask: %s" % replies["ask " + name]
    return line


def section_span(md, name):
    m = re.search(r"^## %s\s*$" % re.escape(name), md, re.M)
    if not m:
        return None
    nxt = re.search(r"^## ", md[m.end():], re.M)
    return m.start(), m.end() + nxt.start() if nxt else len(md)


def convert(md, skill, lists):
    sentences = []
    for nodes in skill["compiled"]:
        sentences += [s for s in plain_sentences(nodes, lists, (skill["action"], skill["object"])) if s not in sentences]
    out = md
    span = section_span(out, "Sentences")
    out = out[:span[0]] + "## People say\n\n" + "\n".join("- " + s for s in sentences) + "\n\n" + out[span[1]:]
    span = section_span(out, "Values")
    if span:
        lines = [needs_line(k, v, skill["replies"]) for k, v in skill["values"].items()]
        out = out[:span[0]] + "## What it needs\n\n" + "\n".join(lines) + "\n\n" + out[span[1]:]
        out = re.sub(r"^- ask \w+:.*\n", "", out, flags=re.M)
    return out


if __name__ == "__main__":
    lang = load_language("en")
    wanted = sys.argv[1:]
    d = os.path.join(language_dir("en"), "skills")
    for s in lang["skills"]:
        if wanted and s["id"] not in wanted or s.get("plain"):
            continue
        path = os.path.join(d, s["id"], "skill.md")
        with open(path, encoding="utf-8") as f:
            md = f.read()
        new = convert(md, s, lang["lists"])
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
        print("%-20s %d templates → %d sentences" % (s["id"], len(s["compiled"]), new.count("\n- ", new.find("## People say"), new.find("\n## ", new.find("## People say") + 5))))
