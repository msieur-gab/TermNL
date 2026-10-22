import { test } from "node:test";
import assert from "node:assert/strict";
import { loadLanguage } from "../core/load-node.js";
import { createAgent } from "../core/agent.js";
import { device } from "./device.js";

const lang = loadLanguage("en");
const agent = (settings = {}) => createAgent({ ...lang, settings, device, random: () => 0 });

test("skill files have no problems", () => assert.deepEqual(lang.errors, []));

test("a template request acts, with values quoted", () => {
  const r = agent().hear("create a file named sprout.md in the ideas folder");
  assert.equal(r.outcome, "act");
  assert.equal(r.command, "touch $HOME'/ideas/sprout.md'");
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
  const r = a.hear("note"); // Documents already has a note.md: no loop, and no second one
  assert.equal(r.reason, "already exists");
  const b = agent();
  b.hear("add a new note inside my documets");
  b.hear("Documents");
  assert.equal(b.hear("memo").command, "touch $HOME'/Documents/memo.md'");
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

// Gab's run, 22 Oct 10:25: opening a file.
test("“open this file”: a pointing word is never a name, so the file is asked", () => {
  const r = agent().hear("open this file");
  assert.equal(r.outcome, "ask");
  assert.equal(r.skill, "open-file");
});

test("“can you please open the note.md” opens it", () => {
  assert.equal(agent().hear("can you please open the note.md").command, "xdg-open $HOME'/note.md'");
});

test("“open the note.md file located inside my Documents folder” opens it there", () => {
  assert.equal(agent().hear("can you please open the note.md file located inside my Documents folder").command, "xdg-open $HOME'/Documents/note.md'");
});

test("opening an app still opens the app", () => {
  assert.equal(agent().hear("open the terminal").command, "setsid 'x-terminal-emulator'");
});

// Where you are (Gab, 22 Oct 10:30: "if i say open or go to Documents folder i imagine getting inside
// its directory"). Files are found on the device, not assumed.
test("opening a folder goes into it; a file is then opened there", () => {
  const a = agent();
  const r = a.hear("open the documents folder");
  assert.equal(r.command, "ls $HOME'/Documents'");
  assert.equal(a.here.label, "Documents");
  assert.equal(a.hear("open note.md").command, "xdg-open $HOME'/Documents/note.md'");
});

test("“go to ideas” then creating a file makes it there", () => {
  const a = agent();
  a.hear("go to ideas");
  assert.equal(a.hear("create a file called plan").command, "touch $HOME'/ideas/plan.md'");
});

test("showing a folder lists it without going into it", () => {
  const a = agent();
  a.hear("show me downloads");
  assert.equal(a.here.label, "home");
});

test("a file not here but in one other folder: asked, then opened there", () => {
  const a = agent();
  const r = a.hear("open report.pdf");
  assert.equal(r.outcome, "ask");
  assert.match(r.say, /Documents/);
  assert.equal(a.hear("yes").command, "xdg-open $HOME'/Documents/report.pdf'");
});

test("the same name in several folders: which one, with chips", () => {
  const a = agent();
  a.hear("go to downloads");
  const r = a.hear("open note.md");
  assert.equal(r.outcome, "ask");
  assert.deepEqual(r.chips.sort(), ["Documents", "home", "ideas"]);
  assert.equal(a.hear("ideas").command, "xdg-open $HOME'/ideas/note.md'");
});

test("a name without its extension, and a typo, still find the file", () => {
  const a = agent();
  a.hear("go to documents");
  assert.equal(a.hear("open groceries").command, "xdg-open $HOME'/Documents/groceries.md'");
  const r = a.hear("open grocries.md");
  assert.equal(r.outcome, "ask");
  assert.match(r.say, /groceries\.md/);
});

test("a file found nowhere is said so, and nothing runs", () => {
  const r = agent().hear("open taxes.pdf");
  assert.equal(r.command, undefined);
  assert.match(r.say, /taxes\.pdf/);
});

test("creating a file that already exists runs nothing", () => {
  const r = agent().hear("create a file called seed.md in ideas");
  assert.equal(r.command, undefined);
  assert.match(r.say, /already/);
});
