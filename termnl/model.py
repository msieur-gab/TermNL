"""The learned part: it recognises the action and the object of a request, in words nobody wrote
down. Carried over from ptiLU, unchanged in method:
  features  words, word pairs, and 3–4 letter fragments of each word (so "rebot" still looks like
            "reboot", and a new form of a known word keeps most of its fragments)
  model     TF-IDF + logistic regression, trained by stochastic gradient descent, then L-BFGS
Two small models instead of one big one: one for the action (about 10 classes), one for the object
(about 12). A skill is a declared pair of the two.

Recognising and training need only the standard library: training runs on the device, when the person
validates what it learned."""
import math
import operator
from array import array

from .text import tokenize


def features(text, toks=None):
    toks = toks if toks is not None else [t["word"] for t in tokenize(text)]
    out = []
    prev = "<s>"
    for t in toks:
        out += ["w:" + t, "b:" + prev + "_" + t]
        p = "<" + t + ">"
        for n in (3, 4):
            out += ["c:" + p[i:i + n] for i in range(len(p) - n + 1)]
        prev = t
    out.append("b:" + prev + "_</s>")
    return out


def _round(x):
    return math.floor(x * 1000 + 0.5) / 1000


def train_classifier(examples, C=8.0, min_df=2, passes=12, rate=2.0, settle=20, seed=7):
    """examples: [{text, label}] → a small JSON-able model {labels, bias, scale, weights}: each weight a whole
    number from -127 to 127 (one byte, as ptiLU stores them), times the model's scale. Half the size of
    decimals, the same decisions (measured 23 Oct: 241 sentences, the tests, Gab's real turns).

    Plain Python, nothing to install, so the board trains itself. What is learned is what numpy learned:
    the same features, TF-IDF, classes balanced, the same penalty on big weights (C), the same best model.
    Two steps get there. Stochastic gradient descent first, one sentence at a time in an order shuffled by a
    fixed seed, the weights averaged over the second half of the passes: cheap, it lands close. Then
    `settle` steps of L-BFGS on all the sentences at once, as numpy did from zero: it settles on the one
    best model, whatever the order, so adding a skill moves only what the skill changes (measured 26 Oct:
    without them, another seed alone moved 31 answers of 665; with 20, 5). Sentences that are the same
    words with the same label are read once, counted as many times."""
    labels = sorted({e["label"] for e in examples})
    K = len(labels)
    li = {l: k for k, l in enumerate(labels)}
    docs = []
    for e in examples:
        c = {}
        for f in features(e["text"]):
            c[f] = c.get(f, 0) + 1
        docs.append(c)
    df = {}
    for d in docs:
        for f in d:
            df[f] = df.get(f, 0) + 1
    vocab = sorted(f for f, c in df.items() if c >= min_df)
    index = {f: j for j, f in enumerate(vocab)}
    n, nf = len(docs), len(vocab)
    idf = [math.log((1 + n) / (1 + df[f])) + 1 for f in vocab]
    y = [li[e["label"]] for e in examples]
    counts = [0] * K
    for k in y:
        counts[k] += 1
    merged = {}  # (row, label) → weight: balanced classes, a sentence said twice counts twice
    for d, k in zip(docs, y):
        r = [(index[f], (1 + math.log(c)) * idf[index[f]]) for f, c in d.items() if f in index]
        norm = math.sqrt(sum(v * v for _, v in r)) or 1
        key = (tuple(sorted((j, round(v / norm, 12)) for j, v in r)), k)
        merged[key] = merged.get(key, 0.0) + n / (K * counts[k])
    rows = [(key[0], key[1], w) for key, w in merged.items()]

    W, b = _sgd(rows, K, nf, C, passes, rate, seed)
    x = [W[j][k] for k in range(K) for j in range(nf)] + b  # one list: the weights class by class, then the biases
    del W
    x = _lbfgs(_objective(rows, K, nf, C), x, max_iter=settle)
    W = [[x[k * nf + j] for k in range(K)] for j in range(nf)]
    b = x[K * nf:]
    scale = max(abs(v) for r in W for v in r) / 127 or 1
    weights = {}
    for j, f in enumerate(vocab):
        ws = [int(round(v / scale)) for v in W[j]]
        if any(abs(v) >= 0.01 for v in W[j]) and any(ws):
            weights[f] = [_round(idf[j])] + ws
    return {"labels": labels, "bias": [_round(v) for v in b], "scale": scale, "weights": weights}


def _sgd(rows, K, nf, C, passes, rate, seed):
    """the first step: close to the best model, quickly → W (feature by feature), b"""
    lam = 1.0 / (C * sum(w for _, _, w in rows))  # the penalty |W|²/2C, shared out over the sentences
    W = [[0.0] * K for _ in range(nf)]  # kept divided by a: the true weights are a·W (the penalty shrinks a)
    b = [0.0] * K
    a = 1.0
    acc, accb, averaged = [[0.0] * K for _ in range(nf)], [0.0] * K, 0
    order = list(range(len(rows)))
    s = seed & 0xFFFFFFFF
    for p in range(passes):
        lr = rate / (1 + p)
        for i in range(len(order) - 1, 0, -1):
            s = (s * 1664525 + 1013904223) & 0xFFFFFFFF
            j = s % (i + 1)
            order[i], order[j] = order[j], order[i]
        for at in order:
            row, gold, w = rows[at]
            sc = b[:]
            for j, v in row:
                av = a * v
                sc = [x + c * av for x, c in zip(sc, W[j])]
            mx = max(sc)
            e = [math.exp(x - mx) for x in sc]
            z = sum(e)
            step = lr * w
            g = [ek / z * step for ek in e]
            g[gold] -= step
            a *= 1 - lr * w * lam
            if a < 1e-6:
                W = [[c * a for c in r] for r in W]
                a = 1.0
            moved = [(k, gk) for k, gk in enumerate(g) if gk > 1e-7 or gk < -1e-7]
            for k, gk in moved:
                b[k] -= gk
            for j, v in row:
                r, f = W[j], v / a
                for k, gk in moved:
                    r[k] -= gk * f
        if p >= passes // 2:
            averaged += 1
            acc = [[x + c * a for x, c in zip(ra, rw)] for ra, rw in zip(acc, W)]
            accb = [x + c for x, c in zip(accb, b)]
    return [[x / averaged for x in r] for r in acc], [x / averaged for x in accb]


def _objective(rows, K, nf, C):
    """x → (the loss on every sentence plus the penalty, its gradient), as the numpy trainer computed them.
    A class whose probability for a sentence is under a millionth of the likeliest is left out of that
    sentence's gradient: it changes nothing measurable and saves most of the time."""
    data = []
    for r, gold, w in rows:
        idx = [j for j, _ in r]
        get = operator.itemgetter(*idx) if len(idx) > 1 else (lambda L, j=idx[0]: (L[j],)) if idx else (lambda L: ())
        data.append((get, idx, [v for _, v in r], gold, w))

    def fg(x):
        Ws = [x[k * nf:(k + 1) * nf] for k in range(K)]
        G = [[0.0] * nf for _ in range(K)]
        gb = [0.0] * K
        f = 0.0
        for get, idx, vals, gold, w in data:
            sc = [bk + _dot(vals, get(Wk)) for bk, Wk in zip(x[K * nf:], Ws)]
            mx = max(sc)
            e = [math.exp(v - mx) for v in sc]
            z = sum(e)
            f += w * (math.log(z) + mx - sc[gold])
            cut = 1e-6 * z
            for k, ek in enumerate(e):
                if ek > cut or k == gold:
                    d = w * (ek / z - (k == gold))
                    gb[k] += d
                    Gk = G[k]
                    for j, v in zip(idx, vals):
                        Gk[j] += d * v
        grad = []
        for Wk, Gk in zip(Ws, G):
            f += _dot(Wk, Wk) / (2 * C)
            grad += [gv + wv / C for gv, wv in zip(Gk, Wk)]  # intercepts not penalised
        return f, grad + gb
    return fg


def _dot(u, v):
    return math.sumprod(u, v) if _SUMPROD else sum(map(operator.mul, u, v))


_SUMPROD = hasattr(math, "sumprod")  # Python 3.12+; the board has 3.13


def _lbfgs(fg, x, m=10, max_iter=150, tol=1e-4):
    """the numpy trainer's L-BFGS, step for step, on plain lists"""
    def axpy(a, u, v):  # a·u + v
        return [a * p + q for p, q in zip(u, v)]

    f, g = fg(x)
    S, Yl, rho = [], [], []
    for _ in range(max_iter):
        if max(map(abs, g)) < tol:
            break
        d = [-v for v in g]
        alpha = [0.0] * len(S)
        for j in range(len(S) - 1, -1, -1):
            alpha[j] = rho[j] * _dot(S[j], d)
            d = axpy(-alpha[j], Yl[j], d)
        c = _dot(S[-1], Yl[-1]) / _dot(Yl[-1], Yl[-1]) if S else 1 / math.sqrt(_dot(g, g))
        d = [c * v for v in d]
        for j in range(len(S)):
            d = axpy(alpha[j] - rho[j] * _dot(Yl[j], d), S[j], d)
        slope = _dot(g, d)
        if slope >= 0:
            d, S, Yl, rho = [-v for v in g], [], [], []
            slope = _dot(g, d)
        step = 1.0
        for _ in range(30):
            xn = axpy(step, d, x)
            fn, gn = fg(xn)
            if fn <= f + 1e-4 * step * slope:
                break
            step *= 0.5
        sv = array("d", [p - q for p, q in zip(xn, x)])  # 8 bytes a number, not 32: ten of each are kept
        yv = array("d", [p - q for p, q in zip(gn, g)])
        sy = _dot(sv, yv)
        if sy > 1e-10:
            S.append(sv)
            Yl.append(yv)
            rho.append(1 / sy)
            if len(S) > m:
                S.pop(0)
                Yl.pop(0)
                rho.pop(0)
        x, g = xn, gn
        rel = abs(f - fn) / max(1, abs(f))
        f = fn
        if rel < 1e-9:
            break
    return x


def classify(model, text, toks=None):
    """→ [{label, p}] sorted, most likely first"""
    counts = {}
    for f in features(text, toks):
        counts[f] = counts.get(f, 0) + 1
    known, norm = [], 0.0
    for f, c in counts.items():
        row = model["weights"].get(f)
        if not row:
            continue
        v = (1 + math.log(c)) * row[0]
        known.append((row, v))
        norm += v * v
    norm = math.sqrt(norm) or 1
    s = list(model["bias"])
    scale = model.get("scale", 1)  # one byte per weight (train_classifier)
    for row, v in known:
        for k in range(len(s)):
            s[k] += row[k + 1] * scale * v / norm
    mx = max(s)
    e = [math.exp(v - mx) for v in s]
    z = sum(e)
    return sorted(({"label": l, "p": e[k] / z} for k, l in enumerate(model["labels"])), key=lambda x: -x["p"])
