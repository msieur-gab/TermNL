"""Words, lists and small Markdown readers shared by the core. Standard library only."""
import random as _random
import re

# A word: letters of any alphabet or digits, with . _ - ' inside (seed.md, wi-fi, what's).
WORD_RE = re.compile(r"\w(?:[\w.\-']*\w)?|\.\.")  # and "..", the folder above (cd ..)
QUOTES = str.maketrans({"’": "'", "‘": "'", "`": "'"})


def tokenize(text):
    """[{word, start, end}], words lowercased; offsets index the text with its quotes made plain."""
    clean = text.translate(QUOTES)
    return [{"word": m.group(0).lower(), "start": m.start(), "end": m.end()} for m in WORD_RE.finditer(clean)]


def words(phrase):
    """A phrase as words: "turn off" → ["turn", "off"]"""
    return [t["word"] for t in tokenize(phrase)]


def read_list(md, section=None):
    """"- key: a, b, c" lines of a Markdown section (or of the file before its first section)
    → [{key, rest, words}]"""
    lines = md.split("\n")
    if section:
        at = next((i for i, l in enumerate(lines) if l.strip().lower() == "## " + section.lower()), -1)
        if at < 0:
            return []
        end = next((i for i, l in enumerate(lines) if i > at and l.startswith("## ")), None)
        lines = lines[at + 1:end]
    else:
        end = next((i for i, l in enumerate(lines) if l.startswith("## ")), None)
        lines = lines[:end]
    out = []
    for l in lines:
        m = re.match(r"^- ([^:]+):\s*(.*)$", l)
        if m:
            rest = m.group(2).strip()
            out.append({"key": m.group(1).strip(), "rest": rest, "words": [w.strip() for w in m.group(2).split(",") if w.strip()]})
    return out


def read_pairs(md):
    """"key: value" lines (settings.md, a skill's front matter) → {key: value}"""
    out = {}
    for l in md.split("\n"):
        m = re.match(r"^([a-z][a-z ]*):\s*(.*?)\s*$", l, re.I)
        if m:
            out[m.group(1).strip().lower()] = m.group(2)
    return out


def pick(variants, random=_random.random):
    """One of several written variants ("A | B | C"), picked at random so the agent doesn't repeat itself."""
    found = [v.strip() for v in variants.split("|") if v.strip()]
    return found[int(random() * len(found))] if found else ""


def fill(text, values):
    return re.sub(r"\{([\w@.]+)\}", lambda m: "" if values.get(m.group(1)) is None else str(values[m.group(1)]), text)


def close(a, b):
    """A typo of a word: one letter added, dropped, changed or swapped (two for words of 8 letters or
    more). Short words (under 4 letters) must match exactly: "ssh" is not "ssd"."""
    if a == b:
        return True
    if len(b) < 4 or abs(len(a) - len(b)) > 2:
        return False
    most = 2 if len(b) >= 8 else 1
    d = [[i] + [0] * len(b) for i in range(len(a) + 1)]
    for j in range(1, len(b) + 1):
        d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (0 if a[i - 1] == b[j - 1] else 1))
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[len(a)][len(b)] <= most
