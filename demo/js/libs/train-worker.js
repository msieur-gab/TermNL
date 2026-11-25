// Trains TermNL's model again, away from the page so the conversation goes on (about 3½ minutes, as on the board).
// It gets TermNL's files, the skills taught in the tab among them, and answers with the new model as JSON.

const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";
importScripts(PYODIDE + "pyodide.js");

const TRAIN = `
import json
from termnl.train import train_language
model, n, took = train_language("en")
json.dumps(model, separators=(",", ":"))
`;

onmessage = async ({ data }) => {
  try {
    const py = await loadPyodide({ indexURL: PYODIDE });
    await py.loadPackage("numpy");
    for (const [path, text] of data.files) {
      const where = "/home/pyodide/" + path;
      py.FS.mkdirTree(where.slice(0, where.lastIndexOf("/")));
      py.FS.writeFile(where, text);
    }
    postMessage({ model: py.runPython(TRAIN) });
  } catch (e) {
    postMessage({ error: String((e && e.message) || e).split("\n").filter(Boolean).slice(-3).join(" ") });
  }
};
