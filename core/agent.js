// The dialogue. Every request ends in one of four outcomes:
//   act      understood, everything known, nothing to approve: the command is ready to run
//   ask      a value is missing or isn't on the device, or the request isn't surely understood:
//            a question, with chips when there are choices
//   approve  the action is destructive or needs admin rights: the person approves first
//   abstain  nothing understood, or the settings don't allow it: the agent says so
//
// Understanding comes in two layers:
//   1. a skill's templates, when one reads the sentence exactly (values read precisely);
//   2. the model, which recognises the action and the object in any wording, with values found by
//      their own readers. It acts only when it is sure and knows every word; otherwise it asks
//      "Do you want me to …?", naming the words it doesn't know yet, and a yes teaches it.
//
// The agent never runs anything and never writes a command: it fills in the command a skill
// declares, with every value quoted. Running it is the device's job.

import { parses, best } from "./template.js";
import { classify } from "./model.js";
import { tokenize, words, pick, fill, close } from "./text.js";

const sq = s => "'" + String(s).replace(/'/g, "'\\''") + "'";
// a path's leading $HOME stays outside the quotes, so the shell still expands it
export const quote = p => (p.startsWith("$HOME") ? "$HOME" + (p.length > 5 ? sq(p.slice(5)) : "") : sq(p));

// how sure the model must be of its action × object pair: to act, and to ask at all
const SURE = 0.5, MAYBE = 0.15;

export function createAgent({ lists, skills, model, settings = {}, device, random = Math.random }) {
  let pending = null;
  // where you are, like a terminal's working folder: home at first, moved by "open/go to a folder"
  let here = null;
  const whereNow = () => here || (() => { const h = sys("folder").find(f => f.value === "$HOME"); return h ? { value: h.value, label: h.label } : { value: "$HOME", label: "home" }; })();
  const on = key => /^(on|yes|true)$/i.test(settings[key] || "");
  const sys = kind => (device ? device.list(kind) : []).map(d => ({
    value: d.value, label: d.names[0], phrases: d.names.map(words),
  }));
  // files aren't a list read in advance: they are looked up in the place once it is known
  const listOf = kind => kind === "filetype" ? lists.filetypes : kind === "@sys.file" ? null : kind.startsWith("@sys.") ? sys(kind.slice(5)) : null;
  const slotLists = skill => Object.fromEntries(Object.entries(skill.values).map(([k, v]) => [k, listOf(v.kind)]));
  const reply = (key, values = {}) => fill(pick(lists.replies[key] || key, random), values);
  const small = new Set((lists.answers["small words"] || []).map(p => p.join(" ")));
  const stops = new Set((lists.answers["not a name start"] || []).map(p => p.join(" ")));
  const objectWords = new Set(lists.objects.flatMap(o => (lists.refs[o] || []).filter(ph => ph.length === 1).map(ph => ph[0])));
  const pointing = new Set((lists.answers["pointing words"] || []).map(p => p.join(" ")));
  // "this", "that file": a value that only points can't be known here, so it is asked for instead
  const onlyPoints = v => v.text !== undefined && v.value === undefined &&
    tokenize(v.text).every(t => pointing.has(t.word));

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

  // Layer 1: every skill's best template reading; the top ones (several if they tie).
  function read(text, toks) {
    const found = [];
    for (const skill of skills) {
      const all = [];
      for (const nodes of skill.compiled) all.push(...parses(nodes, toks, lists.refs, slotLists(skill), stops, objectWords));
      const top = all.length ? best(all) : null;
      if (top) found.push({ skill, parse: top });
    }
    if (!found.length) return [];
    const max = Math.max(...found.map(f => f.parse.score));
    return found.filter(f => f.parse.score === max).map(({ skill, parse }) => {
      const vals = {};
      for (const [k, c] of Object.entries(parse.caps)) {
        vals[k] = { text: original(text, toks, c), value: c.value, label: c.label, unknown: !!c.unknown, fuzzy: !!c.fuzzy };
      }
      return { skill, vals, score: max };
    });
  }

  // Values found by their own readers, anywhere in the sentence (when no template read it):
  // a name from a device list or a shared list, a name after "called"/"named", a file-shaped word.
  function readValues(skill, text, toks) {
    const vals = {}, used = new Set();
    for (const [k, spec] of Object.entries(skill.values)) {
      const list = listOf(spec.kind);
      if (!list) continue;
      let hit = null;
      for (const o of list) for (const ph of o.phrases) for (let i = 0; i + ph.length <= toks.length; i++) {
        const exact = ph.every((w, j) => toks[i + j].word === w);
        const fuzzy = !exact && ph.every((w, j) => close(toks[i + j].word, w));
        if ((exact || fuzzy) && (!hit || ph.length > hit.len || (exact && hit.fuzzy))) hit = { o, i, len: ph.length, fuzzy };
      }
      if (hit) { vals[k] = { value: hit.o.value, label: hit.o.label, fuzzy: hit.fuzzy }; for (let j = 0; j < hit.len; j++) used.add(hit.i + j); }
    }
    for (const [k, spec] of Object.entries(skill.values)) {
      if (listOf(spec.kind) || vals[k]) continue;
      const after = toks.findIndex(t => ["called", "named", "titled"].includes(t.word));
      if (after >= 0 && after + 1 < toks.length) {
        let end = after + 1;
        while (end < toks.length && !["in", "inside", "into", "on", "at", "to", "under"].includes(toks[end].word) && !used.has(end)) end++;
        if (end > after + 1) {
          vals[k] = { text: original(text, toks, { start: after + 1, end }) };
          for (let j = after; j < end; j++) used.add(j);
          continue;
        }
      }
      const file = toks.findIndex((t, i) => !used.has(i) && /\.[a-z0-9]{1,5}$/i.test(t.word));
      if (file >= 0) { vals[k] = { text: original(text, toks, { start: file, end: file + 1 }) }; used.add(file); }
    }
    return { vals, used };
  }

  // What the sentence asks for: a template's exact reading, or the model's best action + object.
  function understand(text, toks) {
    const found = read(text, toks);
    if (found.length && found[0].score >= 1) {
      if (found.length > 1) return { how: "choose", options: found };
      return { how: "template", skill: found[0].skill, vals: found[0].vals, p: 1, unknown: [] };
    }
    if (!model) return null;
    const ws = toks.map(t => t.word);
    const pa = classify(model.action, text, ws);
    const po = classify(model.object, text, ws);
    const P = (list, label) => (list.find(x => x.label === label) || { p: 0 }).p;
    let top = null;
    for (const skill of skills) {
      const p = P(pa, skill.action) * P(po, skill.object);
      if (!top || p > top.p) top = { skill, p };
    }
    const none = Math.max(P(pa, "none"), P(po, "none"));
    if (!top || top.p < MAYBE || none > top.p) return null;
    const { vals, used } = readValues(top.skill, text, toks);
    const taught = new Set(model.taught[top.skill.id] || []);
    const unknown = toks.filter((t, i) => !used.has(i) && !small.has(t.word) && !taught.has(t.word)).map(t => t.word);
    return { how: "model", skill: top.skill, vals, p: top.p, unknown };
  }

  const shown = (skill, k, v) => skill.values[k].kind === "secret" ? "•••" : (v.label ?? v.text);
  function display(skill, vals) {
    const out = { output: "{output}" };
    for (const [k, v] of Object.entries(vals)) out[k] = shown(skill, k, v);
    return out;
  }

  function resolve(skill, vals, approved = false) {
    for (const [k, v] of Object.entries(vals)) if (onlyPoints(v)) delete vals[k];
    // a value close to one on the device's list (a typo): confirm it, never use it silently
    for (const [k, v] of Object.entries(vals)) {
      if (v.fuzzy) {
        pending = { skill, vals, waiting: "fuzzy", slot: k, approved };
        return { outcome: "ask", skill: skill.id, say: reply("did you mean", { value: v.label }), chips: [v.label, "no"] };
      }
    }
    // a value said but not on the device's list: ask which one, with the list as chips
    for (const [k, v] of Object.entries(vals)) {
      if (v.unknown) {
        const list = listOf(skill.values[k].kind) || [];
        pending = { skill, vals, waiting: "value", slot: k, approved };
        return { outcome: "ask", skill: skill.id, say: reply("unknown value", { value: `“${v.text}”` }), chips: list.map(o => o.label).slice(0, 8) };
      }
    }
    for (const [k, spec] of Object.entries(skill.values)) {
      if (vals[k]) continue;
      if (spec.default === "here") {
        vals[k] = { ...whereNow() };
      } else if (spec.default) {
        const list = listOf(spec.kind);
        const hit = list && list.find(o => o.value === spec.default || o.label === spec.default || o.phrases.some(p => p.join(" ") === spec.default));
        vals[k] = hit ? { value: hit.value, label: hit.label } : { text: spec.default };
      } else if (spec.required) {
        pending = { skill, vals, waiting: "value", slot: k, approved };
        const list = listOf(spec.kind);
        return { outcome: "ask", skill: skill.id, say: reply(skill.replies["ask " + k]), chips: list ? list.map(o => o.label).slice(0, 8) : [] };
      }
    }
    finishFiletype(skill, vals);
    const found = findFiles(skill, vals, approved);
    if (found) return found;
    if (skill.admin && !on("admin mode")) {
      pending = null;
      return { outcome: "abstain", skill: skill.id, say: reply("admin off"), reason: "admin mode off" };
    }
    if ((skill.admin || skill.approve) && !approved) {
      pending = { skill, vals, waiting: "approve" };
      return withShow({ outcome: "approve", skill: skill.id, say: reply(skill.replies.approve, display(skill, vals)), chips: ["yes", "no"] }, skill, vals);
    }
    return act(skill, vals);
  }

  // Every value known and sure: nothing is left to ask, so an approval can name exactly what runs.
  const complete = (skill, vals) => Object.entries(skill.values).every(([k, spec]) => {
    const v = vals[k];
    if (!v) return !spec.required || !!spec.default;
    return !v.unknown && !v.fuzzy && !onlyPoints(v) && (spec.kind !== "@sys.file" || v.value !== undefined);
  });

  // Files are checked on the device. A file to open must exist: here, or else anywhere in home
  // (one place: "That one?"; several: "Which one?"; none: said so). A file to create must not.
  function findFiles(skill, vals, approved) {
    if (!device || !device.files) return null;
    const placeKey = Object.keys(skill.values).find(k => skill.values[k].kind === "@sys.folder");
    const place = placeKey && vals[placeKey];
    for (const [k, spec] of Object.entries(skill.values)) {
      const v = vals[k];
      if (!v || !place) continue;
      if (spec.new && v.text && device.files(place.value).includes(v.text)) {
        pending = null;
        return { outcome: "abstain", skill: skill.id, say: reply("already", { file: v.text, folder: place.label }), reason: "already exists" };
      }
      if (spec.kind !== "@sys.file" || v.value !== undefined) continue;
      const name = v.text, stem = f => f.replace(/\.[^.]+$/, "");
      const lower = name.toLowerCase();
      const same = f => f.toLowerCase() === lower || (!/\.\w+$/.test(name) && stem(f).toLowerCase() === lower);
      const files = device.files(place.value);
      const hit = files.find(same);
      if (hit) { vals[k] = { value: hit, label: hit }; continue; }
      const typo = files.find(f => close(lower, f.toLowerCase()) || (!/\.\w+$/.test(name) && close(lower, stem(f).toLowerCase())));
      if (typo) { vals[k] = { value: typo, label: typo, text: name, fuzzy: true }; return resolve(skill, vals, approved); }
      const elsewhere = device.find(same).filter(r => r.folder !== place.value);
      if (elsewhere.length === 1) {
        const r = elsewhere[0];
        pending = { waiting: "elsewhere", skill, vals, approved, options: [{ ...r, k, placeKey }] };
        return { outcome: "ask", skill: skill.id, say: reply("elsewhere", { file: r.file, here: place.label, folder: r.label }), chips: ["yes", "no"] };
      }
      if (elsewhere.length > 1) {
        pending = { waiting: "where", skill, vals, approved, options: elsewhere.map(r => ({ ...r, k, placeKey })) };
        const labels = elsewhere.map(r => r.label);
        return { outcome: "ask", skill: skill.id, say: reply("several", { count: elsewhere.length, file: elsewhere[0].file, folders: labels.join(", ") }), chips: labels };
      }
      pending = null;
      return { outcome: "abstain", skill: skill.id, say: reply("not found", { file: name, here: place.label }), reason: "not found" };
    }
    return null;
  }
  const choose = (o, vals) => { vals[o.k] = { value: o.file, label: o.file }; vals[o.placeKey] = { value: o.folder, label: o.label }; };

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

  const commandFor = (skill, vals) => skill.command.split(" ").map(part => {
    if (!part.includes("{")) return part;
    return quote(part.replace(/\{(\w+)\}/g, (_, k) => vals[k] ? (vals[k].value ?? vals[k].text) : ""));
  }).join(" ");
  // "show commands" on: the command is shown when acting, and before it, when the person approves
  const withShow = (out, skill, vals) => { if (on("show commands")) out.show = commandFor(skill, vals); return out; };

  function act(skill, vals) {
    pending = null;
    const command = commandFor(skill, vals);
    if (skill.moves && vals[skill.moves]) here = { value: vals[skill.moves].value, label: vals[skill.moves].label };
    return withShow({ outcome: "act", skill: skill.id, say: reply(skill.replies.done, display(skill, vals)), command }, skill, vals);
  }

  // An answer to "Which folder?": a value on the list, or free text for a text value.
  // "no" stops the request; "yes" answers nothing, so the question is asked again; "call it bikes"
  // gives the name after its lead-in words (en/answers.md, "before a name").
  function fillPending(text, toks) {
    const { skill, vals, slot, approved } = pending;
    if (is(toks, "no")) { pending = null; return { outcome: "abstain", skill: skill.id, say: reply("declined"), reason: "declined" }; }
    const list = listOf(skill.values[slot].kind);
    if (is(toks, "yes")) {
      const v = vals[slot];
      const say = skill.replies["ask " + slot] ? reply(skill.replies["ask " + slot]) : reply("unknown value", { value: `“${v?.text || v?.label || ""}”` });
      return { outcome: "ask", skill: skill.id, say, chips: list ? list.map(o => o.label).slice(0, 8) : [] };
    }
    if (!list) {
      const lead = (lists.answers["before a name"] || []).filter(ph => ph.length < toks.length && ph.every((w, i) => toks[i].word === w))
        .sort((a, b) => b.length - a.length)[0];
      const start = lead ? lead.length : 0;
      vals[slot] = { text: toks.length ? original(text, toks, { start, end: toks.length }) : text.trim() };
      return resolve(skill, vals, approved);
    }
    let hit = null;
    for (const o of list) for (const ph of o.phrases) for (let i = 0; i + ph.length <= toks.length; i++) {
      if (ph.every((w, j) => toks[i + j].word === w) && (!hit || ph.length > hit.len)) hit = { o, len: ph.length };
    }
    if (!hit) {
      return { outcome: "ask", skill: skill.id, say: reply("unknown value", { value: `“${text.trim()}”` }), chips: list.map(o => o.label).slice(0, 8) };
    }
    vals[slot] = { value: hit.o.value, label: hit.o.label };
    return resolve(skill, vals, approved);
  }

  // what understood the last sentence: the template, or the model and how sure it was
  let last = null;
  function hear(text) {
    last = null;
    const r = respond(text);
    if (last) { r.how = last.how; if (last.p !== undefined) r.p = Math.round(last.p * 100) / 100; if (last.unknown?.length) r.unknown = last.unknown; }
    return r;
  }

  function respond(text) {
    const toks = clean(text);
    if (!toks.length) return { outcome: "abstain", say: reply("abstain") };
    if (is(toks, "cancel")) { pending = null; return { outcome: "abstain", say: reply("cancelled"), reason: "cancelled" }; }

    if (pending?.waiting === "approve") {
      const { skill, vals } = pending;
      if (is(toks, "yes")) return act(skill, vals);
      if (is(toks, "no")) { pending = null; return { outcome: "abstain", skill: skill.id, say: reply("declined"), reason: "declined" }; }
      pending = null; // something else: a new request
    }
    if (pending?.waiting === "understand") {
      const { skill, vals, text: asked, approves } = pending;
      if (is(toks, "yes")) { pending = null; const r = resolve(skill, vals, !!approves); r.teach = { skill: skill.id, text: asked }; return r; }
      if (is(toks, "no")) { pending = null; return { outcome: "abstain", say: reply("declined"), reason: "declined", inbox: asked }; }
      pending = null;
    }
    if (pending?.waiting === "elsewhere" || pending?.waiting === "where") {
      const { skill, vals, approved, options } = pending;
      const said = toks.map(t => t.word).join(" ");
      const o = pending.waiting === "elsewhere" ? (is(toks, "yes") ? options[0] : null)
        : options.find(x => words(x.label).join(" ") === said);
      if (o) { pending = null; choose(o, vals); return resolve(skill, vals, approved); }
      if (is(toks, "no")) { pending = null; return { outcome: "abstain", skill: skill.id, say: reply("declined"), reason: "declined" }; }
      pending = null;
    }
    if (pending?.waiting === "fuzzy") {
      const { skill, vals, slot, approved } = pending;
      const v = vals[slot];
      if (is(toks, "yes") || words(v.label).join(" ") === toks.map(t => t.word).join(" ")) {
        vals[slot] = { value: v.value, label: v.label };
        pending = null;
        return resolve(skill, vals, approved);
      }
      if (is(toks, "no")) {
        const list = listOf(skill.values[slot].kind) || [];
        pending = { skill, vals, waiting: "value", slot, approved };
        return { outcome: "ask", skill: skill.id, say: reply("unknown value", { value: `“${v.text || v.label}”` }), chips: list.map(o => o.label).slice(0, 8) };
      }
      pending = { ...pending, waiting: "value" }; // another folder named instead: read it as the answer
    }
    if (pending?.waiting === "choose") {
      const said = toks.map(t => t.word).join(" ");
      const chosen = pending.options.find(o => words(o.skill.label).join(" ") === said);
      if (chosen) { pending = null; return resolve(chosen.skill, chosen.vals); }
    }
    if (is(toks, "help")) {
      pending = null;
      const names = skills.map(s => s.label);
      return { outcome: "act", say: reply("help", { skills: names.join(", ") }), chips: names };
    }

    const u = understand(text, toks);
    last = u && u.how !== "choose" ? u : null;
    const sure = u && (u.how === "template" || (u.how === "model" && u.p >= SURE && !u.unknown.length));
    // While a question waits, what the person says answers it, unless it clearly asks for something
    // else (another skill, surely understood). The same skill said again adds its values to the
    // question; then whatever is still asked for is filled from the words themselves.
    if (pending?.waiting === "value") {
      // another request: a skill's own sentence, or the model sure of another skill AND an action word
      // said ("open…", "check…"); a lone word like "note" is always an answer
      const saysAction = lists.actions.some(a => (lists.refs[a] || []).some(ph =>
        toks.some((_, i) => ph.length && i + ph.length <= toks.length && ph.every((w, j) => toks[i + j].word === w))));
      const other = sure && u.skill.id !== pending.skill.id && (u.how === "template" || saysAction);
      if (!other) {
        if (sure && u.skill.id === pending.skill.id) {
          for (const [k, v] of Object.entries(u.vals)) if (!pending.vals[k] || pending.vals[k].unknown) pending.vals[k] = v;
          if (pending.vals[pending.slot]) { last = null; const { skill, vals, approved } = pending; pending = null; return resolve(skill, vals, approved); }
        }
        last = null; // an answer, not a new request: nothing to report about understanding it
        return fillPending(text, toks);
      }
    }

    if (!u) { pending = null; return { outcome: "abstain", say: reply("abstain"), reason: "no skill", inbox: text }; }
    if (u.how === "choose") {
      pending = { waiting: "choose", options: u.options };
      const labels = u.options.map(f => f.skill.label);
      return { outcome: "ask", say: reply("choose", { options: labels.join(" or ") }), chips: labels };
    }
    pending = null;
    if (sure) return resolve(u.skill, u.vals);

    // understood, but not surely: ask before doing anything, naming the words it doesn't know
    if (u.skill.admin && !on("admin mode")) {
      return { outcome: "abstain", skill: u.skill.id, say: reply("sounds like", { label: u.skill.label }), reason: "admin mode off" };
    }
    const label = u.skill.label;
    const named = u.unknown.map(w => `“${w}”`).join(", ");
    let say = u.unknown.length ? reply("not sure", { words: named, label }) : reply("confirm", { label });
    // A skill that needs approval asks its own question, so the person approves once, knowingly, but
    // only when every value is known: otherwise this yes only confirms the skill, and the approval
    // comes later, naming what will run.
    const approves = (u.skill.admin || u.skill.approve) && complete(u.skill, u.vals);
    pending = { waiting: "understand", skill: u.skill, vals: u.vals, text, approves };
    const out = { outcome: "ask", skill: u.skill.id, say, chips: ["yes", "no"], unknown: u.unknown, p: Math.round(u.p * 100) / 100 };
    if (approves) {
      out.say = (u.unknown.length ? reply("new words", { words: named }) + " " : "") + reply(u.skill.replies.approve, display(u.skill, u.vals));
      withShow(out, u.skill, u.vals);
    }
    return out;
  }

  return { hear, get pending() { return pending; }, get here() { return whereNow(); } };
}
