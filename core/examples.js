// Training sentences made from the skills' own templates: each template becomes many sentences,
// with its optional words in and out, each alternative, each word for its action and object, and
// sample values. Authors write a few readable lines; the model learns from all their variations.

import { words } from "./text.js";

// Sample values for training only. Real values come from the device at run time.
const SAMPLES = {
  text: ["bikes", "recipes", "notes", "todo", "draft", "seed.md", "photos 2024", "ideas for the trip", "report", "budget"],
  secret: ["hunter2", "s3cret"],
  "@sys.folder": ["documents", "downloads", "photos", "music", "projects", "my home folder", "ideas"],
  "@sys.service": ["ssh", "nginx", "the web server", "docker", "the music server", "bluetooth service"],
  "@sys.network": ["home", "office wifi", "cafe"],
  "@sys.app": ["terminal", "firefox", "the browser", "editor", "files"],
};

function samplesFor(kind, lists) {
  if (kind === "filetype") return lists.filetypes.flatMap(t => t.phrases.map(p => p.join(" ")));
  return SAMPLES[kind] || SAMPLES.text;
}

// one random walk through a template
function walk(nodes, lists, skill, rnd) {
  const out = [];
  for (const n of nodes) {
    if (n.t === "w") out.push(n.w);
    else if (n.t === "ref") { const ph = lists.refs[n.name]; out.push(ph[Math.floor(rnd() * ph.length)].join(" ")); }
    else if (n.t === "slot") { const s = samplesFor(skill.values[n.name].kind, lists); out.push(s[Math.floor(rnd() * s.length)]); }
    else if (n.t === "alt") {
      if (n.opt && rnd() < 0.5) continue;
      out.push(walk(n.alts[Math.floor(rnd() * n.alts.length)], lists, skill, rnd));
    }
  }
  return out.filter(Boolean).join(" ");
}

export function rng(seed = 7) {
  let s = seed >>> 0;
  return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
}

// → [{ text, skill, action, object }], deduplicated
export function examples(skills, lists, { perTemplate = 40, seed = 7 } = {}) {
  const rnd = rng(seed);
  const seen = new Set();
  const out = [];
  for (const skill of skills) for (const nodes of skill.compiled) {
    for (let i = 0; i < perTemplate; i++) {
      const text = walk(nodes, lists, skill, rnd);
      const key = skill.id + "|" + text;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push({ text, skill: skill.id, action: skill.action, object: skill.object });
    }
  }
  return out;
}

// The words a skill has been taught: every word of its generated sentences.
export function taughtWords(exs) {
  const by = {};
  for (const e of exs) { const s = (by[e.skill] ||= new Set()); for (const w of words(e.text)) s.add(w); }
  return by;
}
