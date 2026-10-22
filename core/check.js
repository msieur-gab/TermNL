// node core/check.js — stops with each skill file's problem, or says how many skills are fine.
import { loadLanguage } from "./load-node.js";
const lang = process.argv[2] || "en";
const { skills, errors } = loadLanguage(lang);
if (errors.length) { for (const e of errors) console.error(e); process.exit(1); }
console.log(`${skills.length} skills in ${lang}, no problems.`);
