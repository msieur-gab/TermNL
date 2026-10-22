// Loads a language's lists and skills from disk (Node). The browser does the same with fetch.
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { load } from "./skills.js";
import { readPairs } from "./text.js";

export const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");

export function loadLanguage(lang = "en", root = ROOT) {
  const dir = join(root, lang);
  const read = f => readFileSync(join(dir, f), "utf8");
  const lists = { actions: read("actions.md"), objects: read("objects.md"), filetypes: read("filetypes.md"), answers: read("answers.md") };
  const skills = {};
  for (const id of readdirSync(join(dir, "skills")).sort()) {
    const f = join(dir, "skills", id, "skill.md");
    if (existsSync(f)) skills[id] = readFileSync(f, "utf8");
  }
  const out = load({ lists, skills });
  const m = join(root, "model", lang + ".json");
  if (existsSync(m)) out.model = JSON.parse(readFileSync(m, "utf8"));
  return out;
}

export function loadSettings(root = ROOT) {
  return readPairs(readFileSync(join(root, "settings.md"), "utf8"));
}
