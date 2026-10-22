import { test } from "node:test";
import assert from "node:assert/strict";
import { loadLanguage } from "../core/load-node.js";
import { createAgent } from "../core/agent.js";
import { device } from "./device.js";

const lang = loadLanguage("en");
const agent = (settings = {}) => createAgent({ ...lang, settings, device, random: () => 0 });

test("skill files have no problems", () => assert.deepEqual(lang.errors, []));

test("a template request acts, with values quoted", () => {
  const r = agent().hear("create a file named seed.md in the ideas folder");
  assert.equal(r.outcome, "act");
  assert.equal(r.command, "touch $HOME'/ideas/seed.md'");
});

test("a missing name is asked for, and the answer completes the request", () => {
  const a = agent();
  assert.equal(a.hear("make a new folder").outcome, "ask");
  const r = a.hear("bike photos");
  assert.equal(r.outcome, "act");
  assert.equal(r.command, "mkdir -p $HOME'/bike photos'");
});

test("a folder not on the device is asked about, with the real folders as chips", () => {
  const a = agent();
  const r = a.hear("create a folder called seeds in the garden folder");
  assert.equal(r.outcome, "ask");
  assert.ok(r.chips.includes("ideas"));
  assert.equal(a.hear("ideas").command, "mkdir -p $HOME'/ideas/seeds'");
});

test("a file type gives the extension; Markdown by default", () => {
  assert.equal(agent().hear("create a python file called test").command, "touch $HOME'/test.py'");
  assert.equal(agent().hear("make a new file named todo").command, "touch $HOME'/todo.md'");
});

test("admin mode off: nothing that needs admin runs", () => {
  const r = agent().hear("restart the pi");
  assert.equal(r.outcome, "abstain");
  assert.equal(r.reason, "admin mode off");
});

test("admin mode on: approval every time", () => {
  const a = agent({ "admin mode": "on" });
  assert.equal(a.hear("turn off the wifi").outcome, "approve");
  assert.equal(a.hear("yes").command, "nmcli radio wifi off");
  assert.equal(a.hear("turn off the wifi").outcome, "approve");
  assert.equal(a.hear("no").reason, "declined");
});

test("other wording: the model understands, and checks first when a word is new", () => {
  const a = agent();
  const r = a.hear("is there enough space for a movie");
  assert.equal(r.skill, "check-storage");
  assert.equal(r.outcome, "ask");
  assert.ok(r.unknown.includes("movie"));
  const y = a.hear("yes");
  assert.equal(y.command, "df -h /");
  assert.deepEqual(y.teach, { skill: "check-storage", text: "is there enough space for a movie" });
});

test("nothing understood: abstain, and the sentence goes to the inbox", () => {
  const r = agent().hear("what's the weather tomorrow");
  assert.equal(r.outcome, "abstain");
  assert.equal(r.inbox, "what's the weather tomorrow");
});

test("a name can't inject a command", () => {
  const r = agent().hear("create a folder called x'; rm -rf ~; echo '");
  assert.equal(r.outcome, "act");
  assert.ok(r.command.startsWith("mkdir -p $HOME'/x'\\''"));
});

// Gab's first request in the playground, 22 Oct, and its relatives: a name must never swallow a place,
// and a misspelled folder is confirmed, never ignored.
test("“add a new note inside my documets”: the folder is confirmed, then the name asked", () => {
  const a = agent();
  const r = a.hear("add a new note inside my documets");
  assert.equal(r.outcome, "ask");
  assert.match(r.say, /Documents/);
  const n = a.hear("yes");
  assert.equal(n.outcome, "ask");
  assert.equal(a.hear("shopping list").command, "touch $HOME'/Documents/shopping list.md'");
});

test("a misspelled folder can be refused and chosen from the list", () => {
  const a = agent();
  a.hear("make a folder called seeds in documets");
  const r = a.hear("no");
  assert.equal(r.outcome, "ask");
  assert.ok(r.chips.includes("ideas"));
  assert.equal(a.hear("ideas").command, "mkdir -p $HOME'/ideas/seeds'");
});

test("a name never starts with a place word", () => {
  const r = agent().hear("make a folder for my bike photos");
  assert.equal(r.outcome, "ask");
  assert.equal(agent().hear("create a file in documents").outcome, "ask");
});

test("a place without a name: the name is asked, the place kept", () => {
  const a = agent();
  assert.equal(a.hear("create a file in documents").outcome, "ask");
  assert.equal(a.hear("draft").command, "touch $HOME'/Documents/draft.md'");
});

test("another name for a folder still finds it", () => {
  assert.equal(agent().hear("new folder called bikes inside docs").command, "mkdir -p $HOME'/Documents/bikes'");
});

// Follow-ups (22 Oct, Gab's playground run): an answer to a question is an answer, unless the person
// clearly asks for something else.
test("an answer that is also a skill word fills the question, no loop", () => {
  const a = agent();
  a.hear("add a new note inside my documets");
  a.hear("Documents");
  assert.equal(a.hear("note").command, "touch $HOME'/Documents/note.md'");
});

test("the same request said again completes the question with what it adds", () => {
  const a = agent();
  a.hear("create a file in documents");
  assert.equal(a.hear("create a file called draft").command, "touch $HOME'/Documents/draft.md'");
});

test("a clearly different request replaces the question", () => {
  const a = agent();
  a.hear("create a file in documents");
  assert.equal(a.hear("how much space is left").skill, "check-storage");
});

test("the folder confirmed earlier is kept until the file is made (Gab's run, 22 Oct)", () => {
  const a = agent();
  a.hear("add a new note inside my documets");
  a.hear("Documents");
  assert.equal(a.hear("note.txt").command, "touch $HOME'/Documents/note.txt'");
});
