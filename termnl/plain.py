"""Plain sentences: how a person writes a skill without learning a grammar (24 Oct 2026, a proposal).

A skill's `## People say` holds sentences as people say them. Four marks, all from everyday writing:

  words         written as said; a word for an action or an object (words/actions.md, words/objects.md)
                stands for all its words: "make a folder" also hears "create a directory"
  a/b           one of these words: "called/named"
  ( … )         may be left out: "make a (new) folder"
  {value}       a value, said under ## What it needs
  "…"           a word kept as it is, even when it is a word for an action or object: ("new")

A phrase with several words in an "or" ("what is" or "what's") is written as another sentence. Each
sentence becomes the template the rest of TermNL already reads (template.py), so matching, training and
the tests work the same; this file only reads the plainer form.

`## What it needs` says each value in words from words/values.md:

  - {name}: a new name. If it's missing, ask: What should I call it? | What name should it have?
  - {place}: a folder on the device. If it's not said: where you are."""
import re

from .text import read_list, words

TOKEN = re.compile(r'\(|\)|\{[^}]*\}|"[^"]*"|[^\s(){}"]+')


def phrases_of(lists):
    """every phrase of an action or object → the names it is a word for"""
    out = {}
    for name in lists["actions"] + lists["objects"]:
        for ph in lists["refs"].get(name, []):
            out.setdefault(tuple(ph), []).append(name)
    return out


def ref(names, own, said):
    """the action or object a phrase stands for; the skill's own first, when a word is in two families"""
    if len(names) == 1:
        return names[0]
    mine = [n for n in names if n in own]
    if len(mine) == 1:
        return mine[0]
    raise ValueError('"%s" is a word for %s: write it in quotes to mean only the word, or use another word'
                     % (said, " and ".join(names)))


def to_template(sentence, lists, own=()):
    """a plain sentence → the template it means: "make a (new) folder called/named {name}" →
    "<create> a [new] <folder> (called|named) {name}". Raises ValueError, as compile_template does."""
    known, out, run = phrases_of(lists), [], []

    def flush():
        i = 0
        while i < len(run):
            hit = next((n for n in range(len(run) - i, 0, -1) if tuple(run[i:i + n]) in known), 0)
            if hit:
                out.append("<%s>" % ref(known[tuple(run[i:i + hit])], own, " ".join(run[i:i + hit])))
                i += hit
            else:
                out.append(run[i])
                i += 1
        del run[:]

    depth = 0
    for tok in TOKEN.findall(sentence.strip()):
        if tok in "()":
            flush()
            depth += 1 if tok == "(" else -1
            if depth < 0:
                raise ValueError('a ")" closes nothing in "%s"' % sentence)
            out.append("[" if tok == "(" else "]")
        elif tok.startswith("{"):
            flush()
            out.append(tok)
        elif tok.startswith('"'):
            flush()
            out.extend(words(tok[1:-1]))
        elif "/" in tok:
            flush()
            items = [w for w in tok.split("/") if w]
            if len(items) < 2 or any(len(words(w)) != 1 for w in items):
                raise ValueError('"%s": a / joins single words; write a phrase as another sentence' % tok)
            alts = []
            for w in items:
                names = known.get(tuple(words(w)))
                alts.append("<%s>" % ref(names, own, w) if names else words(w)[0])
            out.append("(%s)" % "|".join(alts))
        else:
            run.extend(words(tok))
    flush()
    if depth:
        raise ValueError('a "(" is never closed in "%s"' % sentence)
    return " ".join(out)


def read_needs(lines, values_md):
    """## What it needs → ({name: {kind, required, new, default}}, {"ask name": replies}, [problems])"""
    kinds = {e["key"].lower(): e["words"] for e in read_list(values_md, "Kinds")}
    when = {e["key"]: e["rest"].lower() for e in read_list(values_md, "When it's missing")}
    defaults = [(e["key"], e["rest"]) for e in read_list(values_md, "Defaults")]
    values, replies, problems = {}, {}, []
    for line in lines:
        m = re.match(r"^- \{(\w+)\}:\s*(.+)$", line.strip())
        if not m:
            continue
        name, rest = m.groups()
        kind_words, _, more = rest.partition(".")
        kind = kinds.get(kind_words.strip().lower())
        if not kind:
            problems.append('{%s}: "%s" is not a kind of value (words/values.md: %s)' % (name, kind_words.strip(), ", ".join(kinds)))
            continue
        v = {"kind": kind[0], "required": False}
        if "new" in kind[1:]:
            v["new"] = True
        more = more.strip()
        ask, default = when.get("ask", "if it's missing, ask"), when.get("default", "if it's not said")
        if more.lower().startswith(ask):
            v["required"] = True
            replies["ask " + name] = more[len(ask):].lstrip(" :")
        elif more.lower().startswith(default):
            said = more[len(default):].lstrip(" :").rstrip(". ")
            v["default"] = said
            for words_, takes in defaults:
                pattern = "^" + re.escape(words_).replace(re.escape("{value}"), r"\{?(\w+)\}?") + "$"
                hit = re.match(pattern, said, re.I)
                if hit:
                    v["default"] = takes.replace("{value}", hit.group(1)) if hit.groups() else takes
                    break
        elif more:
            problems.append('{%s}: after the kind, write "If it\'s missing, ask: …" or "If it\'s not said: …"' % name)
        values[name] = v
    return values, replies, problems
