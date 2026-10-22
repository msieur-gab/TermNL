// Sentence templates, in the spirit of Home Assistant's hassil:
//   word        a word that must be there
//   (a|b c)     one of these
//   [a|b]       one of these, or nothing
//   <create>    any word for the action or object "create" (en/actions.md, en/objects.md)
//   {place}     a value; what it may hold comes from the skill's ## Values
// No learning: a template matches or it doesn't, and the match says which words were what.

import { tokenize, words, close } from "./text.js";

export function compile(template) {
  const src = template.trim();
  let i = 0;
  const err = msg => { throw new Error(`${msg} in "${src}" at ${i}`); };

  function seq(stop) {
    const out = [];
    while (i < src.length) {
      const c = src[i];
      if (stop.includes(c)) return out;
      if (c === " ") { i++; continue; }
      if (c === "[" || c === "(") {
        i++;
        const alts = [seq("|" + (c === "[" ? "]" : ")"))];
        while (src[i] === "|") { i++; alts.push(seq(c === "[" ? "|]" : "|)")); }
        if (src[i] !== (c === "[" ? "]" : ")")) err("unclosed " + c);
        i++;
        out.push({ t: "alt", opt: c === "[", alts });
      } else if (c === "{" || c === "<") {
        const close = c === "{" ? "}" : ">";
        const end = src.indexOf(close, i);
        if (end < 0) err("unclosed " + c);
        const name = src.slice(i + 1, end).trim();
        out.push(c === "{" ? { t: "slot", name } : { t: "ref", name });
        i = end + 1;
      } else if ("])|}>".includes(c)) {
        err("unexpected " + c);
      } else {
        let j = i;
        while (j < src.length && !" []()|{}<>".includes(src[j])) j++;
        for (const w of words(src.slice(i, j))) out.push({ t: "w", w });
        i = j;
      }
    }
    if (stop) err("expected " + stop);
    return out;
  }
  return seq("");
}

// The names a compiled template uses: { slots: Set, refs: Set }
export function uses(nodes, acc = { slots: new Set(), refs: new Set() }) {
  for (const n of nodes) {
    if (n.t === "slot") acc.slots.add(n.name);
    else if (n.t === "ref") acc.refs.add(n.name);
    else if (n.t === "alt") n.alts.forEach(a => uses(a, acc));
  }
  return acc;
}

// Every way the words can be read by the template.
//   refs:  name → [[word, ...], ...]               phrases for <name>
//   slots: name → null (free text) | [{ value, label, phrases: [[word...]] }]   a list
// A list value not on the list is still read: close to a listed one (a typo), it is marked fuzzy and
// confirmed; otherwise marked unknown and asked about. Free text never starts with a place word
// (stops: "in", "inside", "for"…), so a name can't swallow the place that follows it, and never
// ends with an object word (ends: "folder", "file"…), so "the ideas folder" isn't a name.
export function parses(nodes, toks, refs, slots, stops = new Set(), ends = new Set()) {
  const out = [];
  const n = toks.length;
  const at = (phrase, pos) => phrase.length > 0 && pos + phrase.length <= n &&
    phrase.every((w, k) => toks[pos + k].word === w);
  const near = (phrase, pos) => phrase.length > 0 && pos + phrase.length <= n &&
    phrase.every((w, k) => close(toks[pos + k].word, w)) && !at(phrase, pos);

  function m(list, i, pos, caps, score, k) {
    if (i === list.length) return k(pos, caps, score);
    const node = list[i];
    const next = (p, c, s) => m(list, i + 1, p, c, s, k);
    if (node.t === "w") {
      if (pos < n && toks[pos].word === node.w) next(pos + 1, caps, score + 1);
    } else if (node.t === "ref") {
      for (const ph of refs[node.name] || []) if (at(ph, pos)) next(pos + ph.length, caps, score + ph.length);
    } else if (node.t === "alt") {
      if (node.opt) next(pos, caps, score);
      for (const a of node.alts) m(a, 0, pos, caps, score, next);
    } else if (node.t === "slot") {
      const list = slots[node.name];
      if (list) {
        for (const v of list) for (const ph of v.phrases) {
          if (at(ph, pos)) next(pos + ph.length, { ...caps, [node.name]: { start: pos, end: pos + ph.length, value: v.value, label: v.label } }, score + ph.length);
          else if (near(ph, pos)) next(pos + ph.length, { ...caps, [node.name]: { start: pos, end: pos + ph.length, value: v.value, label: v.label, fuzzy: true } }, score + ph.length - 1);
        }
      }
      if (pos < n && stops.has(toks[pos].word)) return;
      // free text, or a list value that isn't on the list (read, but scored down)
      for (let end = pos + 1; end <= n; end++) {
        if (!list && ends.has(toks[end - 1].word)) continue; // "the ideas folder" is a folder, not a name
        const cap = { start: pos, end };
        if (list) cap.unknown = true;
        next(end, { ...caps, [node.name]: cap }, score - (list ? 2 : 0));
      }
    }
  }

  m(nodes, 0, 0, {}, 0, (pos, caps, score) => { if (pos === n) out.push({ caps, score }); });
  return out;
}

// The best reading: most words recognised, then fewest unknown values, then the shortest free text.
export function best(found) {
  const unknown = p => Object.values(p.caps).filter(c => c.unknown).length;
  const free = p => Object.values(p.caps).reduce((s, c) => s + (c.value === undefined ? c.end - c.start : 0), 0);
  return [...found].sort((a, b) => b.score - a.score || unknown(a) - unknown(b) || free(a) - free(b))[0];
}

export { tokenize };
