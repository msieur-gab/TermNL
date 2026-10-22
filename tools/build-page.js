// node tools/build-page.js — one self-contained playground page (core + skills + model inlined):
//   docs/index.html            for GitHub Pages
//   build/playground.html      the same page without the document wrapper, for publishing elsewhere
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { ROOT, loadLanguage } from "../core/load-node.js";
import { device } from "../test/device.js";

const strip = src => src.split("\n")
  .filter(l => !/^import /.test(l) && !/^export \{/.test(l))
  .map(l => l.replace(/^export (function|const|let)/, "$1"))
  .join("\n");
const core = ["text", "template", "model", "skills", "agent"]
  .map(f => `// ---- core/${f}.js\n` + strip(readFileSync(join(ROOT, "core", f + ".js"), "utf8"))).join("\n");

const lang = "en";
const read = f => readFileSync(join(ROOT, lang, f), "utf8");
const lists = { actions: read("actions.md"), objects: read("objects.md"), filetypes: read("filetypes.md"), answers: read("answers.md") };
const { skills: loaded, model } = loadLanguage(lang);
const skills = Object.fromEntries(loaded.map(s => [s.id, read(`skills/${s.id}/skill.md`)]));
const deviceLists = Object.fromEntries(["folder", "service", "app", "network"].map(k => [k, device.list(k)]));
const fileTree = Object.fromEntries(device.list("folder").map(f => [f.value, device.files(f.value)]));

const bundle = `const TermLU = (() => {
${core}
const files = ${JSON.stringify({ lists, skills })};
const lang = load(files);
if (lang.errors.length) console.error(lang.errors);
const deviceLists = ${JSON.stringify(deviceLists)};
const fileTree = ${JSON.stringify(fileTree)};
return { createAgent, lang: { lists: lang.lists, skills: lang.skills }, model: ${JSON.stringify(model)},
  device: { list: kind => deviceLists[kind] || [], files: folder => fileTree[folder] || [],
    find: test => Object.entries(fileTree).flatMap(([folder, files]) => files.filter(test)
      .map(file => ({ folder, file, label: deviceLists.folder.find(d => d.value === folder).names[0] }))) } };
})();`;

const page = readFileSync(join(ROOT, "tools", "page.html"), "utf8").replace("/*BUNDLE*/", () => bundle);
mkdirSync(join(ROOT, "build"), { recursive: true });
mkdirSync(join(ROOT, "docs"), { recursive: true });
writeFileSync(join(ROOT, "build", "playground.html"), page);
writeFileSync(join(ROOT, "docs", "index.html"), `<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n</head>\n<body>\n${page}\n</body>\n</html>\n`);
console.log(`playground: ${Math.round(page.length / 1024)} KB`);
