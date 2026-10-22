// node core/train.js [lang] — trains the action and object models from the skill files and the
// out-of-scope examples, and writes model/<lang>.json.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { loadLanguage, ROOT } from "./load-node.js";
import { examples, taughtWords } from "./examples.js";
import { trainClassifier } from "./model.js";
import { readList } from "./text.js";

export function trainLanguage(lang = "en", root = ROOT) {
  const { lists, skills, errors } = loadLanguage(lang, root);
  if (errors.length) throw new Error(errors.join("\n"));
  const exs = examples(skills, lists);
  const none = readFileSync(join(root, lang, "out-of-scope.md"), "utf8").split("\n")
    .filter(l => l.startsWith("- ")).map(l => l.slice(2).trim());
  const noneEx = none.flatMap(text => [text, text]); // counted twice: there are few of them
  const t0 = Date.now();
  const action = trainClassifier([...exs.map(e => ({ text: e.text, label: e.action })), ...noneEx.map(text => ({ text, label: "none" }))]);
  const object = trainClassifier([...exs.map(e => ({ text: e.text, label: e.object })), ...noneEx.map(text => ({ text, label: "none" }))]);
  const taught = Object.fromEntries(Object.entries(taughtWords(exs)).map(([k, s]) => [k, [...s].sort()]));
  return { model: { lang, action, object, taught }, sentences: exs.length, seconds: (Date.now() - t0) / 1000 };
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const lang = process.argv[2] || "en";
  const { model, sentences, seconds } = trainLanguage(lang);
  mkdirSync(join(ROOT, "model"), { recursive: true });
  const out = join(ROOT, "model", lang + ".json");
  const json = JSON.stringify(model);
  writeFileSync(out, json);
  console.log(`${sentences} sentences, trained in ${seconds}s, ${Math.round(json.length / 1024)} KB → model/${lang}.json`);
}
