// Reads skill files and the shared lists, and checks them. A skill is one action + object pair:
//
//   ---
//   does: create file
//   admin: no          needs admin rights (only runs with admin mode on, after approval)
//   approve: no        always asks for approval first (destructive, or cuts a connection)
//   ---
//   ## Sentences       templates (core/template.js)
//   ## Values          - name: kind[, required][, default: x]
//   ## Command         one line; {value} is filled in and quoted
//   ## Replies         - key: variant | variant
//
// Kinds: text, secret, a shared list (filetype), or a device list (@sys.folder, @sys.service,
// @sys.network, @sys.app).

import { compile, uses } from "./template.js";
import { readList, readPairs, words } from "./text.js";

export const DEVICE_KINDS = ["folder", "service", "network", "app"];

export function readLists(files) {
  const refs = {}, kinds = { actions: [], objects: [] };
  for (const name of ["actions", "objects"]) {
    for (const { key, words: ws } of readList(files[name])) { refs[key] = ws.map(words); kinds[name].push(key); }
  }
  const filetypes = readList(files.filetypes).map(({ key, words: ws }) => {
    const m = key.match(/^(.+?)\s*\((\w+)\)$/);
    const value = m ? m[1].trim() : key;
    return { value, ext: m ? m[2] : value, label: value, phrases: ws.map(words) };
  });
  const answers = {};
  for (const { key, words: ws } of readList(files.answers)) answers[key] = ws.map(words);
  const replies = {};
  for (const { key, rest } of readList(files.answers, "Replies")) replies[key] = rest;
  return { refs, actions: kinds.actions, objects: kinds.objects, filetypes, answers, replies };
}

function section(md, name) {
  const lines = md.split("\n");
  const at = lines.findIndex(l => l.trim().toLowerCase() === "## " + name.toLowerCase());
  if (at < 0) return null;
  const end = lines.findIndex((l, i) => i > at && l.startsWith("## "));
  return lines.slice(at + 1, end < 0 ? undefined : end);
}

export function readSkill(id, md) {
  const front = md.startsWith("---") ? md.slice(3, md.indexOf("\n---", 3)) : "";
  const meta = readPairs(front);
  const sentences = (section(md, "Sentences") || []).filter(l => l.startsWith("- ")).map(l => l.slice(2).trim());
  const values = {};
  for (const { key, words: parts } of readList(md, "Values")) {
    const v = { kind: parts[0] || "text", required: false };
    for (const p of parts.slice(1)) {
      if (p === "required") v.required = true;
      else if (p.startsWith("default:")) v.default = p.slice(8).trim();
    }
    values[key] = v;
  }
  const command = (section(md, "Command") || []).map(l => l.trim().replace(/^`+|`+$/g, "")).find(l => l && !l.startsWith("#")) || "";
  const replies = {};
  for (const { key, rest } of readList(md, "Replies")) replies[key] = rest;
  return {
    id, does: meta.does || "", label: meta.label || meta.does || id,
    admin: /^yes$/i.test(meta.admin || ""), approve: /^yes$/i.test(meta.approve || ""),
    sentences, values, command, replies,
  };
}

// Problems that stop a skill from working, as "skill: reason" lines. Empty means fine.
export function check(skill, lists) {
  const errs = [];
  const say = msg => errs.push(`${skill.id}: ${msg}`);
  // does: "<action> <object>"; an action may be two words (turn off, shut down)
  const action = lists.actions.filter(a => skill.does === a || skill.does.startsWith(a + " "))
    .sort((a, b) => b.length - a.length)[0];
  const object = action ? skill.does.slice(action.length).trim() : "";
  skill.action = action; skill.object = object;
  if (!skill.does) say("no does: line");
  else if (!action) say(`does: "${skill.does}" starts with no action from en/actions.md`);
  else if (!lists.objects.includes(object)) say(`unknown object "${object}" (en/objects.md)`);
  if (!skill.sentences.length) say("no sentences");
  const used = new Set();
  skill.compiled = [];
  for (const s of skill.sentences) {
    try {
      const nodes = compile(s);
      skill.compiled.push(nodes);
      const u = uses(nodes);
      for (const r of u.refs) if (!lists.refs[r]) say(`<${r}> is not an action or object, in "${s}"`);
      for (const v of u.slots) {
        used.add(v);
        if (!skill.values[v]) say(`{${v}} is not declared in ## Values, in "${s}"`);
      }
    } catch (e) { say(e.message); }
  }
  for (const [name, v] of Object.entries(skill.values)) {
    const k = v.kind;
    const known = k === "text" || k === "secret" || k === "filetype" ||
      (k.startsWith("@sys.") && DEVICE_KINDS.includes(k.slice(5)));
    if (!known) say(`value ${name}: unknown kind "${k}"`);
    if (v.required && !v.default && !skill.replies["ask " + name]) say(`value ${name} is required but has no "ask ${name}" reply`);
    if (!used.has(name) && !skill.command.includes(`{${name}}`)) say(`value ${name} is used by no sentence and no command`);
  }
  for (const m of skill.command.matchAll(/\{(\w+)\}/g)) if (!skill.values[m[1]]) say(`command uses {${m[1]}}, not declared`);
  if (!skill.replies.done) say('no "done" reply');
  if ((skill.admin || skill.approve) && !skill.replies.approve) say('needs approval but has no "approve" reply');
  for (const [key, text] of Object.entries(skill.replies)) {
    for (const m of text.matchAll(/\{(\w+)\}/g)) {
      if (!skill.values[m[1]] && m[1] !== "output") say(`reply "${key}" uses {${m[1]}}, which is no value`);
    }
  }
  return errs;
}

export function load({ lists: listFiles, skills: skillFiles }) {
  const lists = readLists(listFiles);
  const skills = [];
  const errors = [];
  for (const [id, md] of Object.entries(skillFiles)) {
    const s = readSkill(id, md);
    errors.push(...check(s, lists));
    skills.push(s);
  }
  const does = new Map();
  for (const s of skills) {
    if (does.has(s.does)) errors.push(`${s.id}: "does: ${s.does}" is also ${does.get(s.does)}`);
    does.set(s.does, s.id);
  }
  return { lists, skills, errors };
}
