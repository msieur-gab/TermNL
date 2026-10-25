"""Plain sentences: how a person writes a skill without learning a grammar (24 Oct 2026, a proposal).

A skill's `## People say` holds sentences as people say them. Four marks, all from everyday writing:

  words         written as said; a word for an action or an object (words/actions.md, words/objects.md)
                stands for all its words: "make a folder" also hears "create a directory" (an action once
                per sentence: in "make a new folder", "new" is just the word new)
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
    known, out, run, said = phrases_of(lists), [], [], set()

    def family(words_):
        """the family a phrase stands for, or None: an action already said in the sentence is a plain word
        the second time ("make a new folder": "new" is a word for create, but nobody means "make a make")"""
        names = known.get(tuple(words_))
        if not names:
            return None
        name = ref(names, own, " ".join(words_))
        if name in said:
            return None
        if name in lists["actions"]:  # an object may come back ("a folder in the projects folder")
            said.add(name)
        return name

    def flush():
        i = 0
        while i < len(run):
            hit = next((n for n in range(len(run) - i, 0, -1) if tuple(run[i:i + n]) in known), 0)
            name = family(run[i:i + hit]) if hit else None
            if name:
                out.append("<%s>" % name)
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
                name = ref(names, own, w) if names else None
                alts.append("<%s>" % name if name and name not in said else words(w)[0])
            said.update(n for n in (ref(known[tuple(words(w))], own, w) for w in items if tuple(words(w)) in known) if n in lists["actions"])
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


AFTER_TO = {"to", "into", "onto", "in", "inside"}  # before the folder something goes to, when the skill moves things
AFTER_FROM = {"from", "of"}


def also_template(line, skill, lists):
    """An "Also said" line as a template, so it is read like a People say line (reader.py, since 25 Oct 2026):
    a word for the skill's own action or object stands for all its words ("is my pi ok" also hears "is my
    board ok"), a word from words/samples.md or a file-shaped word is the value it stands for ("put todo.txt in
    the projects folder" → "put {name} in the {to} folder"), everything else is the word as written. The
    folder slot is the one things go to after "to", "in", "into", or the one that says where things are
    after "from"; a skill with one folder slot has no choice to make."""
    ws = words(line)
    action, obj, values = skill.get("action"), skill.get("object"), skill["values"]
    refs = lists["refs"]
    phrases = {}
    for name in (action, obj):
        for ph in refs.get(name, []):
            phrases.setdefault(tuple(ph), name)
    for objects, phs in skill.get("own", []):  # its own words for its action, when their object is said
        if any(tuple(ph) in {tuple(ws[i:i + len(ph)]) for i in range(len(ws))} for o in objects for ph in refs.get(o, [])):
            for ph in phs:
                phrases.setdefault(tuple(ph), action)
    exts = {x for t in lists["filetypes"] for x in t.get("exts", [t["ext"]])}
    by_kind = {}
    for k, spec in values.items():
        by_kind.setdefault(spec["kind"], []).append(k)
    samples = {}
    for kind, names in by_kind.items():
        found = [" ".join(p) for t in lists["filetypes"] for p in t["phrases"]] if kind == "filetype" else lists["samples"].get(kind, [])
        for v in found:
            samples.setdefault(tuple(words(v)), kind)
    text_slots = [k for k, spec in values.items() if spec["kind"] in ("text", "@sys.file")]
    leads = {ph[0] for ph in lists["conversation"].get("before a name", []) if len(ph) == 1}  # called, named
    folders = by_kind.get("@sys.folder", [])
    out, i, taken, said = [], 0, set(), set()
    small = {"the", "a", "an", "my", "this", "that", "your", "our"}

    def folder_slot(at):
        before = next((ws[j] for j in range(at - 1, -1, -1) if ws[j] not in small), "")
        if len(folders) == 1:
            return folders[0]
        to = [k for k in folders if values[k]["required"] and not values[k].get("default")]
        at = [k for k in folders if values[k].get("default")]
        if before in AFTER_TO and to:
            return to[0]
        if before in AFTER_FROM and at:
            return at[0]
        return next((k for k in folders if k not in taken), folders[0]) if folders else None

    while i < len(ws):
        hit = next((n for n in range(min(4, len(ws) - i), 0, -1) if tuple(ws[i:i + n]) in phrases), 0)
        if hit and phrases[tuple(ws[i:i + hit])] not in said:  # an action once per sentence: in "make a new file", new is just new
            name = phrases[tuple(ws[i:i + hit])]
            if name == action:
                said.add(name)
            out.append("<%s>" % name)
            i += hit
            continue
        hit = next((n for n in range(min(4, len(ws) - i), 0, -1) if tuple(ws[i:i + n]) in samples), 0)
        if hit and i and ws[i - 1] in leads and text_slots:  # "a folder called projects": the name, not a folder on the device
            kind = "text"
            slot = next((k for k in text_slots if k not in taken), text_slots[0])
        elif hit:
            kind = samples[tuple(ws[i:i + hit])]
            slot = folder_slot(i) if kind == "@sys.folder" else next((k for k in by_kind[kind] if k not in taken), by_kind[kind][0])
        if hit:
            if slot:
                taken.add(slot)
                out.append("{%s}" % slot)
                i += hit
                continue
        w = ws[i]
        if "." in w and w.rsplit(".", 1)[1] in exts and text_slots:
            slot = next((k for k in text_slots if k not in taken), text_slots[0])
            taken.add(slot)
            out.append("{%s:file}" % slot)  # only a file-shaped word fits here: "create todo.txt" never reads "create the screen brighter"
        else:
            out.append(w)
        i += 1
    if not any(x.startswith("<") or not x.startswith("{") for x in out):
        return None  # nothing but values ("documents"): no sentence to read
    return " ".join(out)
