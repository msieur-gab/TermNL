// node test/measure.js — how many hand-written phrasings TermLU understands, and how it answers.
import { readFileSync } from "node:fs";
import { loadLanguage } from "../core/load-node.js";
import { createAgent } from "../core/agent.js";
import { device } from "./device.js";

const { lists, skills } = loadLanguage("en");
const lines = readFileSync(new URL("./phrasings.md", import.meta.url), "utf8").split("\n")
  .map(l => l.match(/^- ([\w-]+): (.+)$/)).filter(Boolean);
const tally = { right: 0, wrong: 0, abstain: 0 };
for (const [, want, text] of lines) {
  const agent = createAgent({ lists, skills, settings: { "admin mode": "on" }, device, random: () => 0 });
  const r = agent.hear(text);
  const got = r.skill || (r.outcome === "ask" && r.chips ? "choose" : "—");
  const kind = r.outcome === "abstain" && !r.skill ? "abstain" : got === want ? "right" : "wrong";
  tally[kind]++;
  if (process.argv.includes("-v") || kind !== "right") console.log(`${kind.padEnd(8)} ${want.padEnd(18)} ${got.padEnd(18)} ${text}`);
}
console.log(`\n${lines.length} phrasings: ${tally.right} right, ${tally.wrong} wrong skill, ${tally.abstain} not understood`);
