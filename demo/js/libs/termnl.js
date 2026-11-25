// TermNL in the page: Pyodide (Python in the browser) loads TermNL's own files from this repo, and demo.py answers
// what the page asks (/api/say, /api/inbox…) with server.py's own turn, as on the board. Nothing leaves the page but
// the requests for those files.

const ROOT = new URL("../../../", import.meta.url);  // the repo: termnl/, tests/, demo/
const DEMO = new URL("../../demo.py", import.meta.url);
const HOME = "/home/pyodide/";

const files = new Map();  // every file loaded, path → text, handed to the training worker too
let py, api;

// the repo's files, as GitHub lists them on main (on GitHub Pages, the owner and repo are in the address)
async function listed() {
  const onPages = location.hostname.endsWith(".github.io");
  const owner = onPages ? location.hostname.split(".")[0] : "msieur-gab";
  const repo = onPages ? location.pathname.split("/")[1] : "TermNL";
  const r = await fetch(`https://api.github.com/repos/${owner}/${repo}/git/trees/main?recursive=1`);
  if (!r.ok) throw new Error("GitHub didn't list TermNL's files (" + r.status + "). Try again in a few minutes.");
  return (await r.json()).tree
    .filter(t => t.type === "blob" && /^termnl\/.*\.(py|md|json)$/.test(t.path) && !t.path.startsWith("termnl/bin/"))
    .map(t => t.path)
    .concat(["tests/__init__.py", "tests/device.py"]);
}

async function read(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error("couldn't read " + url);
  return r.text();
}

export function write(pyodide, path, text) {
  const where = HOME + path;
  pyodide.FS.mkdirTree(where.slice(0, where.lastIndexOf("/")));
  pyodide.FS.writeFile(where, text);
}

// wakes TermNL up; step(words) says how far along it is
export async function wake(step = () => {}) {
  const [pyodide, paths] = await Promise.all([loadPyodide(), listed()]);
  py = pyodide;
  step("reading its skill files");
  await Promise.all(paths.map(async p => files.set(p, await read(new URL(p, ROOT)))));
  files.set("demo/demo.py", await read(DEMO));
  for (const [path, text] of files) write(py, path, text);
  py.runPython(`import sys; sys.path.insert(0, '${HOME}demo')`);
  api = py.pyimport("demo").api;
}

const session = (() => { try { return crypto.randomUUID(); } catch { return "s" + Math.random().toString(36).slice(2); } })();

// what the page asks TermNL, as it would ask the board's server → its JSON answer
export function call(path, body = {}) {
  if (!api) throw new Error("TermNL is still waking up");
  return JSON.parse(api("POST", path, JSON.stringify({ ...body, session })));
}

// "learn what I taught you": demo.py asks the page to train the model again (window.termnlTrain), in a worker, from the
// skill files as they are in this tab; learning(true/false) says when it starts and ends
export function trainWith(learning = () => {}) {
  window.termnlTrain = taughtJson => {
    const taught = Object.entries(JSON.parse(taughtJson)).map(([id, text]) => [`termnl/languages/en/skills/${id}/skill.md`, text]);
    const worker = new Worker(new URL("./train-worker.js", import.meta.url));
    learning(true);
    worker.onmessage = ({ data }) => {
      worker.terminate();
      learning(false);
      if (data.error) console.error("[termnl] learning failed:", data.error);
      py.pyimport("demo").demo.trained(data.model || null, data.error || null);
    };
    worker.postMessage({ files: [...files].filter(([p]) => !p.endsWith("model.json")).concat(taught) });
  };
}
