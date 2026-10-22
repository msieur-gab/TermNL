"""Sentence templates, in the spirit of Home Assistant's hassil:
  word        a word that must be there
  (a|b c)     one of these
  [a|b]       one of these, or nothing
  <create>    any word for the action or object "create" (en/actions.md, en/objects.md)
  {place}     a value; what it may hold comes from the skill's ## Values
No learning: a template matches or it doesn't, and the match says which words were what."""
from .text import close, words


def compile_template(template):
    src = template.strip()
    i = 0

    def err(msg):
        raise ValueError('%s in "%s" at %d' % (msg, src, i))

    def seq(stop):
        nonlocal i
        out = []
        while i < len(src):
            c = src[i]
            if c in stop:
                return out
            if c == " ":
                i += 1
                continue
            if c in "[(":
                shut = "]" if c == "[" else ")"
                i += 1
                alts = [seq("|" + shut)]
                while i < len(src) and src[i] == "|":
                    i += 1
                    alts.append(seq("|" + shut))
                if i >= len(src) or src[i] != shut:
                    err("unclosed " + c)
                i += 1
                out.append({"t": "alt", "opt": c == "[", "alts": alts})
            elif c in "{<":
                end = src.find("}" if c == "{" else ">", i)
                if end < 0:
                    err("unclosed " + c)
                name = src[i + 1:end].strip()
                out.append({"t": "slot", "name": name} if c == "{" else {"t": "ref", "name": name})
                i = end + 1
            elif c in "])|}>":
                err("unexpected " + c)
            else:
                j = i
                while j < len(src) and src[j] not in " []()|{}<>":
                    j += 1
                out.extend({"t": "w", "w": w} for w in words(src[i:j]))
                i = j
        if stop:
            err("expected " + stop)
        return out

    return seq("")


def uses(nodes, acc=None):
    """The names a compiled template uses: {slots: set, refs: set}"""
    acc = acc or {"slots": set(), "refs": set()}
    for n in nodes:
        if n["t"] == "slot":
            acc["slots"].add(n["name"])
        elif n["t"] == "ref":
            acc["refs"].add(n["name"])
        elif n["t"] == "alt":
            for a in n["alts"]:
                uses(a, acc)
    return acc


def parses(nodes, toks, refs, slots, stops=frozenset(), ends=frozenset()):
    """Every way the words can be read by the template.
      refs:  name → [[word, ...], ...]               phrases for <name>
      slots: name → None (free text) | [{value, label, phrases: [[word...]]}]   a list
    A list value not on the list is still read: close to a listed one (a typo), it is marked fuzzy and
    confirmed; otherwise marked unknown and asked about. Free text never starts with a place word
    (stops: "in", "inside", "for"…), so a name can't swallow the place that follows it, and never
    ends with an object word (ends: "folder", "file"…), so "the ideas folder" isn't a name."""
    out = []
    n = len(toks)

    def at(phrase, pos):
        return len(phrase) > 0 and pos + len(phrase) <= n and all(toks[pos + k]["word"] == w for k, w in enumerate(phrase))

    def near(phrase, pos):
        return (len(phrase) > 0 and pos + len(phrase) <= n and
                all(close(toks[pos + k]["word"], w) for k, w in enumerate(phrase)) and not at(phrase, pos))

    def m(seq, i, pos, caps, score, k):
        if i == len(seq):
            return k(pos, caps, score)
        node = seq[i]

        def nxt(p, c, s):
            return m(seq, i + 1, p, c, s, k)

        if node["t"] == "w":
            if pos < n and toks[pos]["word"] == node["w"]:
                nxt(pos + 1, caps, score + 1)
        elif node["t"] == "ref":
            for ph in refs.get(node["name"], []):
                if at(ph, pos):
                    nxt(pos + len(ph), caps, score + len(ph))
        elif node["t"] == "alt":
            if node["opt"]:
                nxt(pos, caps, score)
            for a in node["alts"]:
                m(a, 0, pos, caps, score, nxt)
        elif node["t"] == "slot":
            found = slots.get(node["name"])
            name = node["name"]
            if found:
                for v in found:
                    for ph in v["phrases"]:
                        if at(ph, pos):
                            nxt(pos + len(ph), {**caps, name: {"start": pos, "end": pos + len(ph), "value": v["value"], "label": v["label"]}}, score + len(ph))
                        elif near(ph, pos):
                            nxt(pos + len(ph), {**caps, name: {"start": pos, "end": pos + len(ph), "value": v["value"], "label": v["label"], "fuzzy": True}}, score + len(ph) - 1)
            if pos < n and toks[pos]["word"] in stops:
                return
            # free text, or a list value that isn't on the list (read, but scored down)
            for end in range(pos + 1, n + 1):
                if found is None and toks[end - 1]["word"] in ends:
                    continue  # "the ideas folder" is a folder, not a name
                cap = {"start": pos, "end": end}
                if found is not None:
                    cap["unknown"] = True
                nxt(end, {**caps, name: cap}, score - (2 if found is not None else 0))

    m(nodes, 0, 0, {}, 0, lambda pos, caps, score: out.append({"caps": caps, "score": score}) if pos == n else None)
    return out


def best(found):
    """The best reading: most words recognised, then fewest unknown values, then the shortest free text."""
    def unknown(p):
        return sum(1 for c in p["caps"].values() if c.get("unknown"))

    def free(p):
        return sum(c["end"] - c["start"] for c in p["caps"].values() if c.get("value") is None)

    return sorted(found, key=lambda p: (-p["score"], unknown(p), free(p)))[0]
