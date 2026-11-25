// The demo page: TermNL woken up in the page, the conversation, and the panel on the left (what TermNL is, the
// sentences to try, the inbox, a skill to teach, the pretend board, the settings, what it can do).

import { $, el, sayButton } from "./util/dom.js";
import { I } from "./util/icons.js";
import { call, trainWith, wake } from "./libs/termnl.js";
import { clear, onSay, say, waitFor } from "./libs/chat.js";

// ---- the panel: beside the conversation on a wide screen, over it on a phone; remembered in this browser
const wrap = $("wrap"), toggle = $("toggle"), narrow = matchMedia("(max-width: 860px)");
function showPanel(open) {
  wrap.classList.toggle("folded", !open);
  toggle.setAttribute("aria-expanded", String(open));
  toggle.innerHTML = I.panel + (open ? "Hide panel" : "Show panel");
  try { if (!narrow.matches) localStorage.termnlPanel = open ? "open" : "folded"; } catch {}
}
let remembered;
try { remembered = localStorage.termnlPanel; } catch {}
showPanel(!narrow.matches && remembered !== "folded");
toggle.onclick = () => showPanel(wrap.classList.contains("folded"));
$("close").onclick = () => showPanel(false);
onSay(() => { if (narrow.matches) showPanel(false); });

// ---- the sentences to try: each list is written in the page (data-pills, "a|b|c"); a folded kind shows its count
for (const p of document.querySelectorAll("[data-pills]")) {
  const said = p.dataset.pills.split("|");
  for (const s of said) p.append(sayButton("pill", s, say));
  const count = p.closest("details")?.querySelector("summary small");
  if (count) count.textContent = said.length;
}
$("form").addEventListener("submit", e => { e.preventDefault(); say($("say").value); $("say").value = ""; });

// ---- the settings
$("admin").onclick = () => {
  const on = $("admin").getAttribute("aria-pressed") !== "true";
  call("/api/settings", { "admin mode": on ? "on" : "off" });
  $("admin").setAttribute("aria-pressed", String(on));
  $("admin").textContent = on ? "on" : "off";
};
$("reset").onclick = () => {
  call("/api/reset");
  clear();
  $("here").textContent = "home";
  if (narrow.matches) showPanel(false);
};

// ---- teaching a skill: the file goes into TermNL's skills folder, in this tab only, and is read at once
const taught = $("taught");
$("teach").onclick = () => {
  const text = $("skill").value;
  const does = (text.match(/^does:\s*(.+)$/m) || [])[1];
  taught.className = "taught";
  if (!does) { taught.className = "taught bad"; taught.textContent = "A skill needs a does: line, an action and an object."; return; }
  const id = does.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  const r = call("/api/teach", { id, text });
  if (r.errors?.length) { taught.className = "taught bad"; taught.textContent = r.errors.join(" "); return; }
  // to try: its first "People say" line, one "Also said" line (known only once the model learns again), and learning
  const section = name => (text.split(new RegExp(`^## ${name}$`, "m"))[1] || "").split(/^## /m)[0];
  const first = section("People say").match(/^- (.+)$/m);
  const also = section("Also said").match(/^- (.+)$/gm) || [];
  const tries = [
    first && first[1].replace(/\(([^()]*)\)/g, (_, x) => x.split("/")[0]).replace(/\{[^}]+\}/g, "").replace(/\s+/g, " ").trim(),
    also.length ? also[Math.max(0, also.length - 2)].slice(2) : null,
    "learn what I taught you",
  ].filter(Boolean);
  taught.replaceChildren(el("span", "", "Learnt. Try:"), ...tries.map(s => sayButton("chip", s, say)));
};

// ---- waking TermNL up
trainWith(on => { $("learning").hidden = !on; });
const ready = wake(step => { $("hello-what").textContent = step; });
waitFor(ready);
try {
  await ready;
  const hello = $("hello");
  if (hello) {
    const chips = el("div", "chips");
    for (const s of ["delete todo.txt", "my disk feels full", "what's the weather tomorrow", "how hot is the board"]) chips.append(sayButton("chip", s, say));
    hello.replaceChildren(el("b", "", "TermNL is ready"), el("span", "", "Talk to the board the way you'd say it, or try one of these:"),
      chips, el("span", "", "More in the panel, where you can also teach it a skill."));
  }
  const board = call("/api/board");
  const LABELS = { folder: "Folders", service: "Services", app: "Apps", running: "Running", network: "Networks", host: "Computers", music: "Music" };
  $("device").replaceChildren(
    ...Object.entries(LABELS).filter(([k]) => board.lists[k]).flatMap(([k, label]) => [el("dt", "", label), el("dd", "", board.lists[k].join(", "))]),
    ...board.files.flatMap(f => [el("dt", "", f.folder + "/"), el("dd", "", f.files.join(", "))]));
  $("count").textContent = board.skills;
  $("teach").disabled = false;
} catch (e) {
  console.error("[termnl]", e);
  const where = $("hello") || $("log").appendChild(el("div", "hello"));
  where.replaceChildren(el("b", "", "TermNL couldn't wake up"), el("span", "", String(e.message || e)));
}
