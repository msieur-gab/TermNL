"""The learned part, since 26 Oct 2026: one classifier over the whole sentence, skill by skill, with the
tagger's reading of the words (tagger.py) in hand.

  features  the words with each value replaced by what it is ("move <file> to <place>"), word pairs,
            3–4 letter fragments of each word (so "rebot" still looks like "reboot"), which kinds of
            value the sentence holds, and the action and object words it says, together ("turn on|music"
            is not "turn on|wifi")
  model     logistic regression, trained by stochastic gradient descent in plain Python, one weight per
            feature and skill, kept only where it isn't zero, each a whole number from -127 to 127 times
            the model's scale (one byte, as ptiLU stored them)

Before this, two models read the action and the object apart (TF-IDF + logistic regression, trained with
numpy): they could not see what a verb means with its object, and the agent had ten rules to make up
for it. Recognising and training both need only the standard library now: training runs on the device,
in a minute or two, when the person says "learn what I taught you"."""
import math

from .tagger import spans


def features(ws, tags):
    """the features of a tagged sentence"""
    masked, out = [], []
    for w, t in zip(ws, tags):
        if t.startswith("V:"):
            if not masked or masked[-1] != "<" + t[2:] + ">":
                masked.append("<" + t[2:] + ">")
        else:
            masked.append(w)
    prev = "<s>"
    for w in masked:
        out += ["w:" + w, "b:" + prev + "_" + w]
        if not w.startswith("<"):
            p = "<" + w + ">"
            for n in (3, 4):
                out += ["c:" + p[i:i + n] for i in range(len(p) - n + 1)]
        prev = w
    out.append("b:" + prev + "_</s>")
    roles = sorted({r for r, _, _ in spans(ws, tags)})
    out += ["has:" + r for r in roles]
    out.append("has:" + "+".join(roles))
    a = " ".join(w for w, t in zip(ws, tags) if t == "A")
    o = " ".join(w for w, t in zip(ws, tags) if t == "O")
    out += ["A=" + a, "O=" + o, "AO=" + a + "|" + o, "A+has=" + a + "|" + "+".join(roles)]
    return out


def _round(x):
    return math.floor(x * 1000 + 0.5) / 1000


def train_classifier(examples, passes=12, rate=0.5, top=6, seed=7):
    """examples: [{features, label}] → {labels, scale, weights}: weights[feature] = [k, w, k, w…], the classes
    it weighs and by how much (bytes, times scale). Logistic regression, trained by stochastic gradient
    descent in plain Python: each sentence's features weigh 1/√n (n features), the gradient is taken on the
    `top` likeliest classes and the right one (the others' probabilities are too small to matter), the rate
    falls with each pass, and the classes are balanced (a skill with few sentences counts as much as one with
    many). The weights are averaged over the last passes, which steadies them."""
    labels = sorted({e["label"] for e in examples})
    index = {l: k for k, l in enumerate(labels)}
    K = len(labels)
    counts = [0] * K
    for e in examples:
        counts[index[e["label"]]] += 1
    weight_of = [len(examples) / (K * c) if c else 0 for c in counts]
    w = {}  # feature → {class: weight}
    acc, averaged = {}, 0
    s = seed & 0xFFFFFFFF
    order = list(range(len(examples)))
    feats = [sorted(set(e["features"])) for e in examples]
    norms = [1 / math.sqrt(len(f) or 1) for f in feats]
    for p in range(passes):
        lr = rate / (1 + p)
        for i in range(len(order) - 1, 0, -1):
            s = (s * 1664525 + 1013904223) & 0xFFFFFFFF
            j = s % (i + 1)
            order[i], order[j] = order[j], order[i]
        for at in order:
            gold, x, f = index[examples[at]["label"]], norms[at], feats[at]
            sc = {}
            for ft in f:
                row = w.get(ft)
                if row:
                    for k, v in row.items():
                        sc[k] = sc.get(k, 0.0) + v * x
            mx = max(sc.values(), default=0.0)
            if mx < 0:
                mx = 0.0  # the classes with no score at all sit at 0
            e = {k: math.exp(v - mx) for k, v in sc.items()}
            z = sum(e.values()) + (K - len(e)) * math.exp(-mx)
            touched = sorted(e, key=lambda k: -e[k])[:top]
            if gold not in touched:
                touched.append(gold)
            step = lr * weight_of[gold]
            for k in touched:
                g = (e.get(k, math.exp(-mx)) / z - (1.0 if k == gold else 0.0)) * x * step
                if abs(g) < 1e-6:
                    continue
                for ft in f:
                    row = w.setdefault(ft, {})
                    row[k] = row.get(k, 0.0) - g
        if p >= passes // 2:  # the second half of the passes is averaged
            averaged += 1
            for ft, row in w.items():
                a = acc.setdefault(ft, {})
                for k, v in row.items():
                    a[k] = a.get(k, 0.0) + v
    final = {ft: {k: v / averaged for k, v in row.items()} for ft, row in acc.items()}
    scale = max((abs(v) for r in final.values() for v in r.values()), default=1) / 127 or 1
    weights = {}
    for ft, r in final.items():
        flat = []
        for k in sorted(r):
            q = int(round(r[k] / scale))
            if q:
                flat += [k, q]
        if flat:
            weights[ft] = flat
    return {"labels": labels, "scale": scale, "weights": weights}


def _scores(model, feats):
    feats = set(feats)
    s = [0.0] * len(model["labels"])
    x = model["scale"] / math.sqrt(len(feats) or 1)
    for f in feats:
        row = model["weights"].get(f)
        if row:
            for i in range(0, len(row), 2):
                s[row[i]] += row[i + 1] * x
    return s


def _softmax(s):
    mx = max(s)
    e = [math.exp(v - mx) for v in s]
    z = sum(e)
    return [v / z for v in e]


def _fit_beta(model, examples, every=5):
    """the temperature that makes the scores honest: the one with the smallest log loss on the training
    sentences (every fifth, as a sample), from a handful of candidates"""
    index = {l: k for k, l in enumerate(model["labels"])}
    sample = examples[::every]
    best, best_loss = 1.0, None
    scored = [(_scores(model, e["features"]), index[e["label"]]) for e in sample]
    for beta in (0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0, 1.5):
        loss = 0.0
        for s, k in scored:
            p = _softmax(s, beta)
            loss -= math.log(max(p[k], 1e-9))
        if best_loss is None or loss < best_loss:
            best, best_loss = beta, loss
    return best


def classify(model, feats):
    """→ [{label, p}] sorted, most likely first"""
    p = _softmax(_scores(model, feats))
    return sorted(({"label": l, "p": p[k]} for k, l in enumerate(model["labels"])), key=lambda x: -x["p"])
