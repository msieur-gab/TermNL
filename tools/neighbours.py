# Test of 22 Oct 2026: does a word embedding find the right taught word for words the model never saw?
# Usage: put glove-wiki-gigaword-50.gz in <dir>/glove/glove50.gz and <dir>/taught.json (model.taught +
# small words), then: python3 tools/neighbours.py <dir>. Result on 22 Oct: 3 useful of 26 (see HANDOFF.md).
import gzip, json, re, sys, numpy as np
D = sys.argv[1]
t = json.load(open(f"{D}/taught.json"))
taught, small = t["taught"], set(t["small"])
skills_of = {}
for sk, ws in taught.items():
    for w in ws: skills_of.setdefault(w, set()).add(sk)
need = set(skills_of)
lines = [re.match(r"^- ([\w-]+): (.+)$", l) for l in open("tests/phrasings.md")]
lines = [(m[1], m[2]) for m in lines if m]
unknown = {}
for want, text in lines:
    for w in re.findall(r"[a-z0-9][a-z0-9'.-]*", text.lower()):
        if w not in small and w not in skills_of: unknown.setdefault(w, []).append((want, text))
need |= set(unknown)
vec = {}
with gzip.open(f"{D}/glove/glove50.gz", "rt", encoding="utf8") as f:
    for line in f:
        w, rest = line.split(" ", 1)
        if w in need: vec[w] = np.array(rest.split(), dtype=np.float32)
pool = [w for w in skills_of if w in vec and len(w) > 2]
M = np.stack([vec[w] / np.linalg.norm(vec[w]) for w in pool])
right = wrong = novec = 0
rows = []
for u, uses in sorted(unknown.items()):
    if u not in vec: novec += 1; rows.append((u, "— no vector", "", "")); continue
    s = M @ (vec[u] / np.linalg.norm(vec[u]))
    top = np.argsort(-s)[:3]
    n = pool[top[0]]
    wants = {w for w, _ in uses}
    ok = bool(skills_of[n] & wants)
    right += ok; wrong += not ok
    rows.append((u, ", ".join(f"{pool[i]} {s[i]:.2f}" for i in top), "right" if ok else "WRONG", "/".join(sorted(wants))))
for r in rows: print(f"{r[0]:<12} {r[2]:<6} {r[1]:<40} want: {r[3]}")
print(f"\n{len(unknown)} untaught words in the phrasings: nearest taught word in the right skill {right}, wrong {wrong}, no vector {novec}")
