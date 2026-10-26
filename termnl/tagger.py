"""The tagger: which word of a sentence is what (since 26 Oct 2026, the feat/tagger branch).

Every word gets one tag:
  A          a word for the action ("turn", "off")
  O          a word for the object ("music", "folder")
  V:role     a value: V:file, V:place (the folder something is in), V:to (the folder it goes to),
             V:folder (a folder acted on), V:name (a new name), V:new, V:words, V:link, V:type,
             V:service, V:running, V:app, V:music, V:host, V:network, V:secret
  _          anything else ("the", "my", "please", a word nobody taught)

The tagger is an averaged perceptron over the word, its neighbours, its shape, which lists it is on
(the device's folders and services, the words for each action and object) and the tag before it,
decoded left to right. It is trained from the skills' own sentences, which label their words
already: in "put {name} in the {to} folder", put is the action, folder the object, and the values are
values. Training takes seconds; tagging a sentence takes well under a millisecond. Standard library only.

Why a tagger: the templates read exactly but cannot doubt, the old action × object model doubted but
could not find values. The tagger finds the values and says what the rest is, so one classifier over
the whole sentence (model.py) can be sure or unsure of a skill with the values already in hand."""
import re

FILE_RE = re.compile(r"^[\w\-]+\.[a-z0-9]{1,5}$", re.I)
ROLE_OF_FOLDER = {"place": "place", "to": "to"}
ROLE_OF_TEXT = {"new": "new", "words": "words", "link": "link"}


def role_of(slot, spec):
    """the tag's role for a skill's value: by its kind, and for folders and names by what it is for"""
    kind = spec["kind"]
    if kind == "@sys.folder":
        return ROLE_OF_FOLDER.get(slot, "folder")
    if kind == "text":
        return ROLE_OF_TEXT.get(slot, "name")
    if kind == "@sys.file":
        return "file"
    if kind == "filetype":
        return "type"
    if kind == "secret":
        return "secret"
    return kind[5:] if kind.startswith("@sys.") else kind


FOLDERS = ("place", "to", "folder")
NAMES = ("name", "new", "words", "link", "file")  # a file is said by its name too


def same_family(a, b):
    return a == b or (a in FOLDERS and b in FOLDERS) or (a in NAMES and b in NAMES)


def shape(word):
    if FILE_RE.match(word):
        return "file"
    if word == "..":
        return "up"
    if any(c.isdigit() for c in word):
        return "digits" if word.isdigit() else "mixed"
    if "." in word:
        return "dotted"
    if "-" in word:
        return "dashed"
    return "word"


class Context:
    """What the tagger may look up while tagging: the words of each list (kind → set of words), the words
    for each action and object (word → names), the small words, the words before a name, the vocabulary."""

    def __init__(self, lists_words, refs, small, leads, vocab):
        self.on = {}  # word → the kinds of list it is on
        for kind, ws in lists_words.items():
            for w in ws:
                self.on.setdefault(w, set()).add(kind)
        self.names = {}  # word → the actions and objects it is a word of
        for name, phrases in refs.items():
            for ph in phrases:
                for w in ph:
                    self.names.setdefault(w, set()).add(name)
        self.small, self.leads, self.vocab = small, leads, vocab


def features(ws, i, ctx):
    """the features of position i that don't depend on the tag before it"""
    w = ws[i]
    prev = ws[i - 1] if i > 0 else "<s>"
    nxt = ws[i + 1] if i + 1 < len(ws) else "</s>"
    # a neighbour nobody taught (a value, most often) is seen as one, not by its letters: "open firefox" and
    # "open gimp" teach the same thing about "open"
    p_ = prev if prev in ctx.vocab or prev == "<s>" else "<unk>"
    n_ = nxt if nxt in ctx.vocab or nxt == "</s>" else "<unk>"
    f = ["b", "w=" + w, "p=" + p_, "n=" + n_, "pw=" + p_ + "|" + w, "wn=" + w + "|" + n_,
         "s3=" + w[-3:], "pre3=" + w[:3], "sh=" + shape(w), "psh=" + shape(prev), "nsh=" + shape(nxt)]
    if i > 1 and (w in ctx.small or w not in ctx.vocab):
        f.append("pp=" + ws[i - 2])  # two words back, only for a small or unknown word: a word of its own speaks for itself
    if w not in ctx.vocab:
        f += ["unk", "unk|p=" + prev, "unk|n=" + nxt, "unk|sh=" + shape(w)]

    if w in ctx.small:
        f.append("small")
    if prev in ctx.leads:
        f.append("plead")
    if w in ctx.leads:
        f.append("lead")
    for kind in ctx.on.get(w, ()):
        f += ["on:" + kind, "on:" + kind + "|p=" + prev]
    for name in ctx.names.get(w, ()):
        f.append("of:" + name)
    for name in ctx.names.get(prev, ()):
        f.append("pof:" + name)
    for name in ctx.names.get(nxt, ()):
        f.append("nof:" + name)
    return f


def with_prev(f, prev_tag, w):
    return f + ["t-1=" + prev_tag, "t-1=" + prev_tag + "|w=" + w, "t-1=" + prev_tag + "|sh=" + shape(w)]


def decode(weights, tags, ws, ctx, static=None):
    """the tag sequence, left to right, each tag chosen with the one before it known (greedy: a hundred
    times cheaper than searching every sequence, and as right on these short sentences, measured 26 Oct)"""
    n = len(ws)
    if not n:
        return []
    K = len(tags)
    static = static or [features(ws, i, ctx) for i in range(n)]
    out, prev = [], "<s>"
    for i in range(n):
        s = [0.0] * K
        for f in with_prev(static[i], prev, ws[i]):
            row = weights.get(f)
            if row:
                for k in range(K):
                    s[k] += row[k]
        k = max(range(K), key=lambda k: s[k])
        prev = tags[k]
        out.append(prev)
    return out


def train(sentences, ctx, passes=8, seed=7, margin=2.0):
    """sentences: [[(word, tag), ...]] → {tags, weights}: an averaged perceptron, weights rounded to two
    decimals and zero rows dropped. Structured updates: the sequence decoded with the current weights
    against the sequence written down."""
    tags = sorted({t for s in sentences for _, t in s})
    K = len(tags)
    index = {t: k for k, t in enumerate(tags)}
    w, total, stamp = {}, {}, {}
    c = 0

    def upd(f, k, v):
        row = w.get(f)
        if row is None:
            row, w[f], total[f], stamp[f] = [0.0] * K, None, [0.0] * K, [0] * K
            w[f] = row
        total[f][k] += (c - stamp[f][k]) * row[k]
        stamp[f][k] = c
        row[k] += v

    s = seed & 0xFFFFFFFF
    order = list(range(len(sentences)))
    statics = [[features([x for x, _ in sent], i, ctx) for i in range(len(sent))] for sent in sentences]
    for _ in range(passes):
        for i in range(len(order) - 1, 0, -1):  # a shuffle of our own, the same every time
            s = (s * 1664525 + 1013904223) & 0xFFFFFFFF
            j = s % (i + 1)
            order[i], order[j] = order[j], order[i]
        for at in order:
            sent = sentences[at]
            ws = [x for x, _ in sent]
            gold = [t for _, t in sent]
            static = statics[at]
            got = decode(w, tags, ws, ctx, static)
            c += 1
            for i in range(len(ws)):
                if got[i] != gold[i] or i and got[i - 1] != gold[i - 1]:
                    for f in with_prev(static[i], gold[i - 1] if i else "<s>", ws[i]):
                        upd(f, index[gold[i]], 1.0)
                    for f in with_prev(static[i], got[i - 1] if i else "<s>", ws[i]):
                        upd(f, index[got[i]], -1.0)
                    continue
                # right, but barely: the right tag must lead the runner-up by a margin, so a word's own weight
                # grows even when the sequence around it carries it (a perceptron only learns from its mistakes)
                feats = with_prev(static[i], gold[i - 1] if i else "<s>", ws[i])
                sc = [0.0] * K
                for f in feats:
                    row = w.get(f)
                    if row:
                        for k in range(K):
                            sc[k] += row[k]
                g = index[gold[i]]
                other = max((k for k in range(K) if k != g), key=lambda k: sc[k])
                if sc[g] - sc[other] < margin:
                    for f in feats:
                        upd(f, g, 0.5)
                        upd(f, other, -0.5)
    out = {}
    for f, row in w.items():
        avg = [round((total[f][k] + (c - stamp[f][k]) * row[k]) / max(1, c), 2) for k in range(K)]
        if any(avg):
            out[f] = avg
    return {"tags": tags, "weights": out}


def spans(ws, tags):
    """the values a tagging names, as [(role, start, end)], neighbours of one role as one value; and the
    action and object words, as (A words, O words)"""
    out, i = [], 0
    while i < len(ws):
        t = tags[i]
        if t.startswith("V:"):
            j = i + 1
            while j < len(ws) and tags[j] == t:
                j += 1
            out.append((t[2:], i, j))
            i = j
        else:
            i += 1
    return out
