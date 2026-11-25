// The conversation: what you say, a short pause (three dots), and TermNL's turn: its reply, what it read, its outcome
// and how it understood, the answers to tap, and the command it would run, shown under every turn.

import { $, el, sayButton } from "../util/dom.js";
import { call } from "./termnl.js";
import { drawn, table } from "./readings.js";

const log = $("log");
const pause = () => new Promise(ok => setTimeout(ok, 450 + Math.random() * 350));
const HOW = r => r.how === "template" ? "read by a template" : r.how === "model" ? `model, ${Math.round(r.p * 100)}% sure` : "";

let before = () => {};  // what the page does when a sentence is said (closes the panel on a phone)
export const onSay = f => { before = f; };
let ready = Promise.resolve();  // TermNL waking up: a sentence said meanwhile waits for it
export const waitFor = p => { ready = p; };

export async function say(text) {
  text = text.trim();
  if (!text) return;
  before();
  $("hello")?.remove();
  for (const b of log.querySelectorAll(".turn .chip")) b.disabled = true;  // an old question's answers
  log.append(el("div", "you", text));
  const typing = el("div", "typing");
  typing.setAttribute("aria-label", "TermNL is answering");
  typing.append(el("span"), el("span"), el("span"));
  log.append(typing);
  log.scrollTop = log.scrollHeight;
  let r;
  try {
    await ready;
    [r] = await Promise.all([call("/api/say", { text }), pause()]);
  } catch (e) {
    r = { outcome: "abstain", say: "TermNL couldn't answer: " + (e.message || e) };
  }
  typing.remove();
  show(r);
  if (r.here) $("here").textContent = r.here;
  if (r.learning) waitLearning();
  showInbox();
}

// learning again: "Done learning" comes as a turn when it happens
async function waitLearning() {
  for (;;) {
    await new Promise(ok => setTimeout(ok, 2000));
    const r = call("/api/learning");
    if (r.say) show({ outcome: "act", skill: "train-model", say: r.say });
    if (!r.learning) break;
  }
}

export function show(r) {
  const turn = el("div", "turn");
  turn.append(el("div", "say", r.say));
  const seen = drawn(r);
  if (seen) turn.append(seen);
  else if (r.table) turn.append(table(r.table));

  const meta = el("div", "meta");
  meta.append(el("span", "out " + r.outcome, r.outcome));
  if (r.skill) meta.append(el("span", "tag", r.skill));
  if (HOW(r)) meta.append(el("span", "", HOW(r)));
  if (r.unknown?.length) meta.append(el("span", "new", "new words: " + r.unknown.join(", ")));
  if (r.reason && r.outcome === "abstain") meta.append(el("span", "", r.reason));
  if (r.ran === "simulated") meta.append(el("span", "new", "simulated: nothing ran"));
  turn.append(meta);

  if (r.chips?.length) {
    const chips = el("div", "chips");
    for (const c of r.chips) chips.append(sayButton("chip", c, t => say(t)));
    turn.append(chips);
  }
  turn.append(command(r));
  log.append(turn);
  log.scrollTop = log.scrollHeight;
}

// the command under every turn: what would run, and why it didn't
function command(r) {
  const cmd = el("div", "cmd" + (r.show ? "" : " none"));
  if (!r.show) {
    cmd.textContent = r.ran === "read" ? "no shell command: TermNL reads the board itself" : "no command";
    return cmd;
  }
  cmd.append(el("b", "", "$ "), document.createTextNode(r.show));
  const why = r.outcome === "approve" ? "waits for your yes"
    : r.ran === "simulated" ? (r["made up"] ? "not run here: its answer is made up" : "not run here")
    : r.ran === "read" ? "its output is made up here" : "";
  if (why) cmd.append(el("i", "", "   # " + why));
  return cmd;
}

// the inbox: what TermNL didn't understand, and the guesses a yes confirmed (what you'd teach it next)
export function showInbox() {
  const items = call("/api/inbox");
  $("inbox-empty").hidden = items.length > 0;
  $("inbox").replaceChildren(...items.slice().reverse().map(i => {
    const li = el("li", i.teach ? "teach" : "");
    li.append(el("span", "", "“" + i.text + "”"), el("small", "", i.teach ? "to teach → " + i.teach : i.reason));
    return li;
  }));
}

export function clear() {
  log.replaceChildren();
}
