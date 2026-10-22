// The learned part: it recognises the action and the object of a request, in words nobody wrote
// down. Carried over from ptiLU (web/runtime.js, web/trainer.js), unchanged in method:
//   features  words, word pairs, and 3–4 letter fragments of each word (so "rebot" still looks like
//             "reboot", and a new form of a known word keeps most of its fragments)
//   model     TF-IDF + logistic regression, trained with L-BFGS, in plain JavaScript
// TermLU trains two small models instead of one big one: one for the action (about 10 classes), one
// for the object (about 12). A skill is a declared pair of the two.

import { tokenize } from "./text.js";

export function features(text, words) {
  const toks = (words || tokenize(text).map(t => t.word));
  const out = [];
  let prev = "<s>";
  for (const t of toks) {
    out.push("w:" + t, "b:" + prev + "_" + t);
    const p = "<" + t + ">";
    for (const n of [3, 4]) for (let i = 0; i + n <= p.length; i++) out.push("c:" + p.slice(i, i + n));
    prev = t;
  }
  out.push("b:" + prev + "_</s>");
  return out;
}

function tfidf(texts, minDf = 2) {
  const docs = texts.map(t => { const c = new Map(); for (const f of features(t)) c.set(f, (c.get(f) || 0) + 1); return c; });
  const df = new Map();
  for (const d of docs) for (const f of d.keys()) df.set(f, (df.get(f) || 0) + 1);
  const vocab = [...df.keys()].filter(f => df.get(f) >= minDf).sort();
  const index = new Map(vocab.map((f, i) => [f, i]));
  const n = texts.length;
  const idf = vocab.map(f => Math.log((1 + n) / (1 + df.get(f))) + 1);
  const rows = docs.map(d => vectorRow(d, index, idf));
  return { vocab, idf, rows };
}

function vectorRow(counts, index, idf) {
  const idx = [], val = [];
  let norm = 0;
  for (const [f, c] of counts) {
    const j = index.get(f);
    if (j === undefined) continue;
    const v = (1 + Math.log(c)) * idf[j];
    idx.push(j); val.push(v); norm += v * v;
  }
  norm = Math.sqrt(norm) || 1;
  return { idx, val: val.map(v => v / norm) };
}

// multinomial logistic regression, balanced classes, L2 (intercepts not penalised)
function logreg(rows, y, K, nf, { C = 8, maxIter = 150 } = {}) {
  const n = rows.length, P = K * nf + K;
  const counts = new Float64Array(K);
  for (const k of y) counts[k]++;
  const sw = y.map(k => n / (K * counts[k]));
  const scores = new Float64Array(K);
  function fg(w, g) {
    g.fill(0);
    let f = 0;
    for (let i = 0; i < n; i++) {
      const { idx, val } = rows[i];
      let mx = -Infinity;
      for (let k = 0; k < K; k++) {
        let s = w[K * nf + k];
        const base = k * nf;
        for (let q = 0; q < idx.length; q++) s += w[base + idx[q]] * val[q];
        scores[k] = s; if (s > mx) mx = s;
      }
      let z = 0;
      for (let k = 0; k < K; k++) { scores[k] = Math.exp(scores[k] - mx); z += scores[k]; }
      f += sw[i] * (Math.log(z) - Math.log(scores[y[i]]));
      for (let k = 0; k < K; k++) {
        const d = sw[i] * (scores[k] / z - (k === y[i] ? 1 : 0));
        if (d === 0) continue;
        const base = k * nf;
        for (let q = 0; q < idx.length; q++) g[base + idx[q]] += d * val[q];
        g[K * nf + k] += d;
      }
    }
    for (let p = 0; p < K * nf; p++) { f += w[p] * w[p] / (2 * C); g[p] += w[p] / C; }
    return f;
  }
  return lbfgs(fg, new Float64Array(P), { maxIter });
}

function lbfgs(fg, x, { m = 10, maxIter = 150, tol = 1e-4 } = {}) {
  const P = x.length;
  let g = new Float64Array(P), f = fg(x, g);
  const S = [], Y = [], rho = [];
  const dot = (a, b) => { let s = 0; for (let i = 0; i < P; i++) s += a[i] * b[i]; return s; };
  const xn = new Float64Array(P), gn = new Float64Array(P), d = new Float64Array(P);
  for (let it = 0; it < maxIter; it++) {
    let gmax = 0;
    for (let i = 0; i < P; i++) gmax = Math.max(gmax, Math.abs(g[i]));
    if (gmax < tol) break;
    for (let i = 0; i < P; i++) d[i] = -g[i];
    const alpha = new Array(S.length);
    for (let j = S.length - 1; j >= 0; j--) { alpha[j] = rho[j] * dot(S[j], d); for (let i = 0; i < P; i++) d[i] -= alpha[j] * Y[j][i]; }
    const gamma = S.length ? dot(S[S.length - 1], Y[Y.length - 1]) / dot(Y[Y.length - 1], Y[Y.length - 1]) : 1 / Math.sqrt(dot(g, g));
    for (let i = 0; i < P; i++) d[i] *= gamma;
    for (let j = 0; j < S.length; j++) { const b = rho[j] * dot(Y[j], d); for (let i = 0; i < P; i++) d[i] += S[j][i] * (alpha[j] - b); }
    let slope = dot(g, d);
    if (slope >= 0) { for (let i = 0; i < P; i++) d[i] = -g[i]; S.length = Y.length = rho.length = 0; slope = dot(g, d); }
    let step = 1, fn;
    for (let ls = 0; ls < 30; ls++) {
      for (let i = 0; i < P; i++) xn[i] = x[i] + step * d[i];
      fn = fg(xn, gn);
      if (fn <= f + 1e-4 * step * slope) break;
      step *= 0.5;
    }
    const s = new Float64Array(P), yv = new Float64Array(P);
    for (let i = 0; i < P; i++) { s[i] = xn[i] - x[i]; yv[i] = gn[i] - g[i]; }
    const sy = dot(s, yv);
    if (sy > 1e-10) { S.push(s); Y.push(yv); rho.push(1 / sy); if (S.length > m) { S.shift(); Y.shift(); rho.shift(); } }
    x.set(xn); g.set(gn);
    const rel = Math.abs(f - fn) / Math.max(1, Math.abs(f));
    f = fn;
    if (rel < 1e-9) break;
  }
  return x;
}

// examples: [{ text, label }] → a small JSON-able model
export function trainClassifier(examples, opts = {}) {
  const labels = [...new Set(examples.map(e => e.label))].sort();
  const K = labels.length;
  const { vocab, idf, rows } = tfidf(examples.map(e => e.text), opts.minDf ?? 2);
  const y = examples.map(e => labels.indexOf(e.label));
  const w = logreg(rows, y, K, vocab.length, opts);
  const nf = vocab.length;
  // per feature, the weights of each class; tiny weights dropped
  const weights = {};
  vocab.forEach((f, j) => {
    const ws = labels.map((_, k) => Math.round(w[k * nf + j] * 1000) / 1000);
    if (ws.some(v => Math.abs(v) >= 0.01)) weights[f] = [Math.round(idf[j] * 1000) / 1000, ...ws];
  });
  const bias = labels.map((_, k) => Math.round(w[K * nf + k] * 1000) / 1000);
  return { labels, bias, weights };
}

// → [{ label, p }] sorted, most likely first
export function classify(model, text, words) {
  const counts = new Map();
  for (const f of features(text, words)) counts.set(f, (counts.get(f) || 0) + 1);
  const known = [];
  let norm = 0;
  for (const [f, c] of counts) {
    const row = model.weights[f];
    if (!row) continue;
    const v = (1 + Math.log(c)) * row[0];
    known.push([row, v]); norm += v * v;
  }
  norm = Math.sqrt(norm) || 1;
  const s = model.bias.slice();
  for (const [row, v] of known) for (let k = 0; k < s.length; k++) s[k] += row[k + 1] * v / norm;
  const mx = Math.max(...s);
  const e = s.map(v => Math.exp(v - mx));
  const z = e.reduce((a, b) => a + b, 0);
  return model.labels.map((label, k) => ({ label, p: e[k] / z })).sort((a, b) => b.p - a.p);
}
