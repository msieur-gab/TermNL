// What the board read, drawn: a reader's table (files with their icons), and gauges for a level (temperature,
// memory, disk, Wi-Fi). demo.py gives each reading whole: r.reading = {kind, level, values}.

import { el } from "../util/dom.js";
import { I, iconOf } from "../util/icons.js";

// a reader's table, as termnl-chat.js draws it; a row's level colours its last cell, a lock marks a network
export function table({ columns, rows, levels = [], marks = [] }, icons = false) {
  const wrap = el("div", "scroll"), t = el("table");
  if (columns.some(Boolean)) {
    const tr = el("tr");
    for (const c of columns) tr.append(el("th", "", c));
    t.append(tr);
  }
  rows.forEach((row, i) => {
    const tr = el("tr");
    row.forEach((c, j) => tr.append(el("td", j === row.length - 1 && levels[i] ? levels[i].replace(/ /g, "-") : "", c)));
    if (icons && row[0] && row.some(Boolean)) { const m = el("span", "ico"); m.innerHTML = iconOf(row[0], row[1]); tr.firstChild.prepend(m); }
    if (marks[i] === "lock") { const m = el("span", "mark"); m.innerHTML = I.lock; tr.firstChild.prepend(m); }
    t.append(tr);
  });
  wrap.append(t);
  return wrap;
}

const num = v => parseFloat(String(v || "").replace(",", "."));
const TEMP = t => (t - 20) / 0.8;  // 20 °C to 100 °C across the track

// one level: its label and value, a filled track, a mark (where a board slows down), a scale under it
function gauge(label, value, percent, level, { mark, scale } = {}) {
  const g = el("div", "gauge " + String(level || "").replace(/ /g, "-"));
  const head = el("div", "g-head");
  head.append(el("span", "", label), el("b", "", value));
  const track = el("div", "g-track"), fill = el("div", "g-fill");
  fill.style.width = Math.max(2, Math.min(100, percent)) + "%";
  track.append(fill);
  if (mark !== undefined) { const m = el("div", "g-mark"); m.style.left = mark + "%"; track.append(m); }
  g.append(head, track);
  if (scale) { const s = el("div", "g-scale"); for (const x of scale) s.append(el("span", "", x)); g.append(s); }
  return g;
}

// → what to draw under a reply, or null when its table says it as well
export function drawn(r) {
  const k = r.reading?.kind, v = r.reading?.values || {}, level = r.reading?.level;
  const box = el("div", "gauges");
  if (k === "temperature" && !isNaN(num(v["@sys.temperature"]))) {
    const t = num(v["@sys.temperature"]), max = num(v["@sys.temperature.max"]) || 80;
    box.append(gauge("Temperature", v["@sys.temperature"], TEMP(t), level,
      { mark: TEMP(max), scale: ["20 °C", `slows down at ${max} °C`, "100 °C"] }));
    return box;
  }
  if (k === "memory") {
    box.append(gauge("Memory used", `${v["@sys.memory.used"]} of ${v["@sys.memory.total"]}`, num(v["@sys.memory.percent"]), level,
      { scale: ["", v["@sys.memory.percent"], ""] }));
    return box;
  }
  if (k === "storage") {
    box.append(gauge("Main disk", `${v["@sys.storage.free"]} free`, num(v["@sys.storage.percent"]), level,
      { scale: ["", `${v["@sys.storage.percent"]} of ${v["@sys.storage.total"]} used`, ""] }));
    return box;
  }
  if ((k === "health" || k === "feeling") && r.table) {
    const [t, m, d] = r.table.levels || [];
    box.append(
      gauge("Temperature", v["@sys.health.temperature"], TEMP(num(v["@sys.health.temperature"])), t, { mark: TEMP(80) }),
      gauge("Memory used", v["@sys.health.memory"], num(v["@sys.health.memory"]), m),
      gauge("Disk used", v["@sys.health.disk"], num(v["@sys.health.disk"]), d, { scale: ["", `running for ${v["@sys.health.uptime"]}`, ""] }));
    return box;
  }
  if (k === "wifi" && v["@sys.wifi.signal"]) {
    box.append(gauge(v["@sys.wifi"] || "Wi-Fi", "signal " + v["@sys.wifi.signal"], num(v["@sys.wifi.signal"]), level));
    return box;
  }
  if (["folder", "files", "has", "recent", "trash"].includes(k) && r.table) return table(r.table, true);
  return null;
}
