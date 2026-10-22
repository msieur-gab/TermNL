// node tests/parity.mjs — the JavaScript agent's replies to tests/conversations.json and the phrasings, as JSON
import { readFileSync } from "node:fs";
import { loadLanguage } from "../core/load-node.js";
import { createAgent } from "../core/agent.js";
import { device } from "../test/device.js";
const lang = loadLanguage("en");
const convs = JSON.parse(readFileSync(new URL("./conversations.json", import.meta.url), "utf8"));
const phr = readFileSync(new URL("./phrasings.md", import.meta.url), "utf8").split("\n").map(l => l.match(/^- [\w-]+: (.+)$/)).filter(Boolean).map(m => [{ "admin mode": "on" }, [m[1]]]);
const pick = r => ({ outcome: r.outcome, skill: r.skill ?? null, say: r.say, command: r.command ?? null, chips: r.chips ?? null, show: r.show ?? null, how: r.how ?? null, unknown: r.unknown ?? null });
console.log(JSON.stringify([...convs, ...phr].map(([settings, turns]) => { const a = createAgent({ ...lang, settings, device, random: () => 0 }); return turns.map(t => pick(a.hear(t))); })));
