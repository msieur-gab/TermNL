// The dialogue. Every request ends in one of four outcomes:
//   act      everything is known and nothing needs approval: the command is ready to run
//   ask      a value is missing or isn't on the device: a question, with chips when there's a list
//   approve  the action is destructive or needs admin rights: the person approves first
//   abstain  no skill reads the sentence, or the settings don't allow it: the agent says so
//
// The agent never runs anything itself and never writes a command: it fills in the command a skill
// declares, with every value quoted. Running it is the device's job.

import { parses, best } from "./template.js";
import { tokenize, words, pick, fill } from "./text.js";

const sq = s => "'" + String(s).replace(/'/g, "'\\''") + "'";
// a path's leading $HOME stays outside the quotes, so the shell still expands it
export const quote = p => (p.startsWith("$HOME") ? "$HOME" + (p.length > 5 ? sq(p.slice(5)) : "") : sq(p));

export function createAgent({ lists, skills, settings = {}, device, random = Math.random }) {
  let pending = null;
  const on = key => /^(on|yes|true)$/i.test(settings[key] || "");
  const sys = kind => (device ? device.list(kind) : []).map(d => ({
    value: d.value, label: d.names[0], phrases: d.names.map(words),
  }));
  const listOf = kind => kind === "filetype" ? lists.filetypes : kind.startsWith("@sys.") ? sys(kind.slice(5)) : null;
  const slotLists = skill => Object.fromEntries(Object.entries(skill.values).map(([k, v]) => [k, listOf(v.kind)]));
  const reply = (key, values = {}) => fill(pick(lists.replies[key] || key, random), values);

  // Fillers ("please", "can you", "for me") are dropped at the start and end of a sentence.
  function clean(text) {
    let toks = tokenize(text);
    const starts = lists.answers["filler start"] || [], ends = lists.answers["filler end"] || [];
    const atStart = ph => ph.length <= toks.length && ph.every((w, i) => toks[i].word === w);
    const atEnd = ph => ph.length <= toks.length && ph.every((w, i) => toks[toks.length - ph.length + i].word === w);
    for (let changed = true; changed;) {
      changed = false;
      for (const ph of starts) if (toks.length > ph.length && atStart(ph)) { toks = toks.slice(ph.length); changed = true; }
      for (const ph of ends) if (toks.length > ph.length && atEnd(ph)) { toks = toks.slice(0, -ph.length); changed = true; }
    }
    return toks;
  }
  const is = (toks, key) => (lists.answers[key] || []).some(ph => ph.length === toks.length && ph.every((w, i) => toks[i].word === w));
  const original = (text, toks, c) => text.replace(/[’‘`]/g, "'").slice(toks[c.start].start, toks[c.end - 1].end);

  // Every skill's best reading of the sentence; the top ones (several if they tie).
  function read(text, toks) {
    const found = [];
    for (const skill of skills) {
      const all = [];
      for (const nodes of skill.compiled) all.push(...parses(nodes, toks, lists.refs, slotLists(skill)));
      const top = all.length ? best(all) : null;
      if (top) found.push({ skill, parse: top });
    }
    if (!found.length) return [];
    const max = Math.max(...found.map(f => f.parse.score));
    return found.filter(f => f.parse.score === max).map(({ skill, parse }) => {
      const vals = {};
      for (const [k, c] of Object.entries(parse.caps)) {
        vals[k] = { text: original(text, toks, c), value: c.value, label: c.label, unknown: !!c.unknown };
      }
      return { skill, vals, score: max };
    });
  }

  const shown = (skill, k, v) => skill.values[k].kind === "secret" ? "•••" : (v.label ?? v.text);

  function resolve(skill, vals) {
    // a value said but not on the device's list: ask which one, with the list as chips
    for (const [k, v] of Object.entries(vals)) {
      if (v.unknown) {
        const list = listOf(skill.values[k].kind) || [];
        pending = { skill, vals, waiting: "value", slot: k };
        return { outcome: "ask", skill: skill.id, say: reply("unknown value", { value: `“${v.text}”` }), chips: list.map(o => o.label).slice(0, 8) };
      }
    }
    for (const [k, spec] of Object.entries(skill.values)) {
      if (vals[k]) continue;
      if (spec.default) {
        const list = listOf(spec.kind);
        const hit = list && list.find(o => o.value === spec.default || o.label === spec.default || o.phrases.some(p => p.join(" ") === spec.default));
        vals[k] = hit ? { value: hit.value, label: hit.label } : { text: spec.default };
      } else if (spec.required) {
        pending = { skill, vals, waiting: "value", slot: k };
        const list = listOf(spec.kind);
        return { outcome: "ask", skill: skill.id, say: reply(skill.replies["ask " + k]), chips: list ? list.map(o => o.label).slice(0, 8) : [] };
      }
    }
    finishFiletype(skill, vals);
    if (skill.admin && !on("admin mode")) {
      pending = null;
      return { outcome: "abstain", skill: skill.id, say: reply("admin off"), reason: "admin mode off" };
    }
    if (skill.admin || skill.approve) {
      pending = { skill, vals, waiting: "approve" };
      return { outcome: "approve", skill: skill.id, say: reply(skill.replies.approve, display(skill, vals)), chips: ["yes", "no"] };
    }
    return act(skill, vals);
  }

  // A file's name gets the extension of its type, unless it already has a known one (seed.md).
  function finishFiletype(skill, vals) {
    const typeKey = Object.keys(skill.values).find(k => skill.values[k].kind === "filetype");
    if (!typeKey || !vals.name) return;
    const name = vals.name.text;
    const ext = (name.match(/\.(\w+)$/) || [])[1];
    const known = lists.filetypes.find(t => t.ext === (ext || "").toLowerCase());
    if (known) { vals[typeKey] = { value: known.value, label: known.label }; return; }
    const type = lists.filetypes.find(t => t.value === vals[typeKey]?.value || t.value === vals[typeKey]?.text) || lists.filetypes[0];
    vals.name = { text: `${name}.${type.ext}` };
  }

  function display(skill, vals) {
    const out = { output: "{output}" };
    for (const [k, v] of Object.entries(vals)) out[k] = shown(skill, k, v);
    return out;
  }

  function act(skill, vals) {
    pending = null;
    const command = skill.command.split(" ").map(part => {
      if (!part.includes("{")) return part;
      return quote(part.replace(/\{(\w+)\}/g, (_, k) => vals[k] ? (vals[k].value ?? vals[k].text) : ""));
    }).join(" ");
    const out = { outcome: "act", skill: skill.id, say: reply(skill.replies.done, display(skill, vals)), command };
    if (on("show commands")) out.show = command;
    return out;
  }

  // An answer to "Which folder?": a value on the list, or free text for a text value.
  function fillPending(text, toks) {
    const { skill, vals, slot } = pending;
    const list = listOf(skill.values[slot].kind);
    if (!list) {
      vals[slot] = { text: toks.length ? original(text, toks, { start: 0, end: toks.length }) : text.trim() };
      return resolve(skill, vals);
    }
    let hit = null;
    for (const o of list) for (const ph of o.phrases) for (let i = 0; i + ph.length <= toks.length; i++) {
      if (ph.every((w, j) => toks[i + j].word === w) && (!hit || ph.length > hit.len)) hit = { o, len: ph.length };
    }
    if (!hit) {
      return { outcome: "ask", skill: skill.id, say: reply("unknown value", { value: `“${text.trim()}”` }), chips: list.map(o => o.label).slice(0, 8) };
    }
    vals[slot] = { value: hit.o.value, label: hit.o.label };
    return resolve(skill, vals);
  }

  function hear(text) {
    const toks = clean(text);
    if (!toks.length) return { outcome: "abstain", say: reply("abstain") };
    if (is(toks, "cancel")) { pending = null; return { outcome: "abstain", say: reply("cancelled"), reason: "cancelled" }; }

    if (pending?.waiting === "approve") {
      const { skill, vals } = pending;
      if (is(toks, "yes")) return act(skill, vals);
      if (is(toks, "no")) { pending = null; return { outcome: "abstain", skill: skill.id, say: reply("declined"), reason: "declined" }; }
      pending = null; // something else: a new request
    }
    if (is(toks, "help")) {
      pending = null;
      const names = skills.map(s => s.label);
      return { outcome: "act", say: reply("help", { skills: names.join(", ") }), chips: names };
    }

    const found = read(text, toks);
    if (pending?.waiting === "choose") {
      const said = toks.map(t => t.word).join(" ");
      const chosen = pending.options.find(o => words(o.skill.label).join(" ") === said);
      if (chosen) { pending = null; return resolve(chosen.skill, chosen.vals); }
    }
    // a full request (two or more words recognised) replaces a pending question; anything else answers it
    if (pending?.waiting === "value" && !(found.length && found[0].score >= 2)) return fillPending(text, toks);

    if (!found.length || found[0].score < 1) {
      pending = null;
      return { outcome: "abstain", say: reply("abstain"), reason: "no skill", inbox: text };
    }
    if (found.length > 1) {
      pending = { waiting: "choose", options: found };
      const labels = found.map(f => f.skill.label);
      return { outcome: "ask", say: reply("choose", { options: labels.join(" or ") }), chips: labels };
    }
    pending = null;
    return resolve(found[0].skill, found[0].vals);
  }

  return { hear, get pending() { return pending; } };
}
