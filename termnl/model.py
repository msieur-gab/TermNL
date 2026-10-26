"""The learned part: it recognises the action and the object of a request, in words nobody wrote
down. Carried over from ptiLU, unchanged in method:
  features  words, word pairs, and 3–4 letter fragments of each word (so "rebot" still looks like
            "reboot", and a new form of a known word keeps most of its fragments)
  model     TF-IDF + logistic regression, trained with L-BFGS
Two small models instead of one big one: one for the action (about 10 classes), one for the object
(about 12). A skill is a declared pair of the two.

Recognising needs only the standard library. Training needs numpy (Debian: python3-numpy): it runs on
the device, when the person validates what it learned."""
import math

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


def train_classifier(examples, C=8.0, max_iter=150, min_df=2):
    """examples: [{text, label}] → a small JSON-able model {labels, bias, scale, weights}: each weight a whole
    number from -127 to 127 (one byte, as ptiLU stores them), times the model's scale. Half the size of
    decimals, the same decisions (measured 23 Oct: 241 sentences, the tests, Gab's real turns)."""
    import numpy as np

    labels = sorted({e["label"] for e in examples})
    K = len(labels)
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
    idf = np.array([math.log((1 + n) / (1 + df[f])) + 1 for f in vocab])
    rows, cols, vals = [], [], []
    for i, d in enumerate(docs):
        r = [(index[f], (1 + math.log(c)) * idf[index[f]]) for f, c in d.items() if f in index]
        norm = math.sqrt(sum(v * v for _, v in r)) or 1
        for j, v in r:
            rows.append(i)
            cols.append(j)
            vals.append(v / norm)
    rows, cols, vals = np.array(rows), np.array(cols), np.array(vals)
    y = np.array([labels.index(e["label"]) for e in examples])
    counts = np.bincount(y, minlength=K)
    sw = n / (K * counts[y])  # balanced classes
    Y = np.zeros((K, n))
    Y[y, np.arange(n)] = 1

    def fg(w):
        W, b = w[:K * nf].reshape(K, nf), w[K * nf:]
        S = np.stack([np.bincount(rows, weights=W[k, cols] * vals, minlength=n) for k in range(K)]) + b[:, None]
        S -= S.max(axis=0)
        E = np.exp(S)
        Z = E.sum(axis=0)
        f = float((sw * (np.log(Z) - S[y, np.arange(n)])).sum())
        D = sw * (E / Z - Y)  # K × n
        G = np.stack([np.bincount(cols, weights=D[k, rows] * vals, minlength=nf) for k in range(K)])
        f += float((W * W).sum() / (2 * C))
        G += W / C  # intercepts not penalised
        return f, np.concatenate([G.ravel(), D.sum(axis=1)])

    w = _lbfgs(fg, np.zeros(K * nf + K), max_iter=max_iter)
    W, b = w[:K * nf].reshape(K, nf), w[K * nf:]
    scale = float(np.abs(W).max()) / 127 or 1
    weights = {}
    for j, f in enumerate(vocab):
        ws = [int(round(float(W[k, j]) / scale)) for k in range(K)]
        if any(abs(v) >= 0.01 for v in W[:, j]) and any(ws):
            weights[f] = [_round(float(idf[j]))] + ws
    return {"labels": labels, "bias": [_round(float(v)) for v in b], "scale": scale, "weights": weights}


def _lbfgs(fg, x, m=10, max_iter=150, tol=1e-4):
    import numpy as np

    f, g = fg(x)
    S, Yl, rho = [], [], []
    for _ in range(max_iter):
        if np.abs(g).max() < tol:
            break
        d = -g
        alpha = [0.0] * len(S)
        for j in range(len(S) - 1, -1, -1):
            alpha[j] = rho[j] * S[j].dot(d)
            d = d - alpha[j] * Yl[j]
        d = d * (S[-1].dot(Yl[-1]) / Yl[-1].dot(Yl[-1]) if S else 1 / math.sqrt(g.dot(g)))
        for j in range(len(S)):
            d = d + S[j] * (alpha[j] - rho[j] * Yl[j].dot(d))
        slope = g.dot(d)
        if slope >= 0:
            d, S, Yl, rho = -g, [], [], []
            slope = g.dot(d)
        step = 1.0
        for _ in range(30):
            xn = x + step * d
            fn, gn = fg(xn)
            if fn <= f + 1e-4 * step * slope:
                break
            step *= 0.5
        s, yv = xn - x, gn - g
        sy = s.dot(yv)
        if sy > 1e-10:
            S.append(s)
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
