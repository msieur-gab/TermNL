// Words, lists and small Markdown readers shared by the core. No dependencies: runs in Node and in
// the browser.

// A word: letters of any alphabet or digits, with . _ - ' inside (seed.md, wi-fi, what's).
const WORD_RE = /[\p{L}\p{N}_](?:[\p{L}\p{N}_.\-']*[\p{L}\p{N}_])?/gu;

export function tokenize(text) {
  const clean = text.replace(/[’‘`]/g, "'");
  const out = [];
  for (const m of clean.matchAll(WORD_RE)) {
    out.push({ word: m[0].toLowerCase(), start: m.index, end: m.index + m[0].length });
  }
  return out;
}

// "- key: a, b, c" lines of a Markdown section (or the whole file) → [{ key, words: [...] }]
export function readList(md, section) {
  let lines = md.split("\n");
  if (section) {
    const at = lines.findIndex(l => l.trim().toLowerCase() === "## " + section.toLowerCase());
    if (at < 0) return [];
    const end = lines.findIndex((l, i) => i > at && l.startsWith("## "));
    lines = lines.slice(at + 1, end < 0 ? undefined : end);
  } else {
    const end = lines.findIndex(l => l.startsWith("## "));
    if (end >= 0) lines = lines.slice(0, end);
  }
  const out = [];
  for (const l of lines) {
    const m = l.match(/^- ([^:]+):\s*(.*)$/);
    if (m) out.push({ key: m[1].trim(), rest: m[2].trim(), words: m[2].split(",").map(w => w.trim()).filter(Boolean) });
  }
  return out;
}

// "key: value" lines (settings.md, a skill's front matter)
export function readPairs(md) {
  const out = {};
  for (const l of md.split("\n")) {
    const m = l.match(/^([a-z][a-z ]*):\s*(.*?)\s*$/i);
    if (m) out[m[1].trim().toLowerCase()] = m[2];
  }
  return out;
}

// One of several written variants ("A | B | C"), picked at random so the agent doesn't repeat itself.
export function pick(variants, random = Math.random) {
  const list = variants.split("|").map(v => v.trim()).filter(Boolean);
  return list[Math.floor(random() * list.length)] || "";
}

export function fill(text, values) {
  return text.replace(/\{(\w+)\}/g, (_, k) => (values[k] ?? ""));
}

// A phrase as words: "turn off" → ["turn", "off"]
export const words = phrase => tokenize(phrase).map(t => t.word);
