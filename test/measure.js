// node test/measure.js — how many hand-written phrasings TermLU understands, and how it answers.
import { readFileSync } from "node:fs";
import { loadLanguage } from "../core/load-node.js";
import { createAgent } from "../core/agent.js";
import { device } from "./device.js";

const { lists, skills, model } = loadLanguage("en");
const lines = readFileSync(new URL("./phrasings.md", import.meta.url), "utf8").split("\n")
  .map(l => l.match(/^- ([\w-]+): (.+)$/)).filter(Boolean);
const tally = { acted: 0, asked: 0, "wrong?": 0, WRONG: 0, abstain: 0 };
for (const [, want, text] of lines) {
  const agent = createAgent({ lists, skills, model, settings: { "admin mode": "on" }, device, random: () => 0 });
  const r = agent.hear(text);
  const got = r.skill || (r.outcome === "ask" && r.chips ? "choose" : "—");
  const kind = r.outcome === "abstain" && !r.skill ? "abstain" : got !== want ? (r.outcome === "ask" ? "wrong?" : "WRONG")
    : r.outcome === "ask" && r.chips && r.chips[0] === "yes" ? "asked" : "acted";
  tally[kind]++;
  if (process.argv.includes("-v") || kind !== "acted") console.log(`${kind.padEnd(8)} ${want.padEnd(18)} ${got.padEnd(18)} ${text}${r.unknown?.length ? "   [new: " + r.unknown.join(", ") + "]" : ""}`);
}
console.log(`\n${lines.length} phrasings: ${tally.acted} understood and handled, ${tally.asked} understood but checked first ("Do you want me to…?"), ${tally["wrong?"]} wrong skill but asked first, ${tally.WRONG} wrong skill acted on or approved, ${tally.abstain} not understood`);
