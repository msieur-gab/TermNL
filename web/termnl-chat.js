// <termnl-chat api="http://board:8810"> — the chat: a log of turns, chips to tap, a line to type in.
// It only knows the API's address, so any page can hold it (this one, a phone app, desk's kiosk).
// Each turn shows the reply; under it, small, what happened: understood how, and what ran.

const css = `
  :host { display: flex; flex-direction: column; min-height: 0; font: inherit; color: var(--text); }
  .log { flex: 1; overflow-y: auto; padding: 16px 0; display: flex; flex-direction: column; gap: 14px; }
  .you { align-self: flex-end; max-width: 80%; background: var(--accent); color: var(--on-accent);
         padding: 8px 12px; border-radius: 14px 14px 4px 14px; }
  .turn { align-self: flex-start; max-width: 88%; display: flex; flex-direction: column; gap: 6px; }
  .say { background: var(--surface); padding: 8px 12px; border-radius: 14px 14px 14px 4px; white-space: pre-wrap; }
  .meta { font-size: 12px; color: var(--muted); display: flex; flex-wrap: wrap; gap: 8px; }
  .meta b { font-weight: 600; }
  .simulated { color: var(--warn); } .failed { color: var(--bad); }
  .cmd { font: 13px/1.4 ui-monospace, "Departure Mono", monospace; background: var(--code); padding: 6px 10px;
         border-radius: 6px; white-space: pre-wrap; overflow-wrap: anywhere; }
  .chips { display: flex; flex-wrap: wrap; gap: 6px; }
  button { font: inherit; cursor: pointer; }
  .chip { border: 1px solid var(--accent); background: none; color: var(--accent); border-radius: 999px; padding: 4px 12px; }
  .chip:hover { background: var(--accent); color: var(--on-accent); }
  form { display: flex; gap: 8px; padding-top: 8px; border-top: 1px solid var(--line); }
  input { flex: 1; min-width: 0; font: inherit; padding: 10px 12px; border-radius: 10px; border: 1px solid var(--line);
          background: var(--surface); color: var(--text); }
  .send { border: 0; background: var(--accent); color: var(--on-accent); border-radius: 10px; padding: 0 16px; }
`;

const session = (() => {
  try { return localStorage.termnlSession ||= crypto.randomUUID(); } catch { return "s" + Math.random().toString(36).slice(2); }
})();

class TermNLChat extends HTMLElement {
  connectedCallback() {
    const root = this.attachShadow({ mode: "open" });
    root.innerHTML = `<style>${css}</style><div class="log" part="log"></div>
      <form><input placeholder="e.g. make a folder called bikes" autocomplete="off" aria-label="Say something">
      <button class="send">Send</button></form>`;
    this.log = root.querySelector(".log");
    this.input = root.querySelector("input");
    root.querySelector("form").addEventListener("submit", e => { e.preventDefault(); this.say(this.input.value); this.input.value = ""; });
  }

  get api() { return (this.getAttribute("api") || "").replace(/\/$/, ""); }

  async post(path, body) {
    const r = await fetch(this.api + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...body, session }) });
    return r.json();
  }

  el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text !== undefined) e.textContent = text; return e; }

  async say(text) {
    text = text.trim();
    if (!text) return;
    this.log.append(this.el("div", "you", text));
    let r;
    try { r = await this.post("/api/say", { text }); }
    catch { r = { outcome: "abstain", say: "I can't reach TermNL." }; }
    this.show(r);
    this.dispatchEvent(new CustomEvent("reply", { detail: r }));
  }

  show(r) {
    const turn = this.el("div", "turn");
    turn.append(this.el("div", "say", r.say));
    if (r.show) turn.append(this.el("div", "cmd", (r.ran === "ran" ? "ran: " : r.outcome === "approve" ? "would run: " : r.ran ? r.ran + ": " : "") + "$ " + r.show));
    if (r.output) turn.append(this.el("div", "cmd", r.output));
    const meta = this.el("div", "meta");
    meta.append(this.el("b", "", r.outcome));
    if (r.skill) meta.append(this.el("span", "", r.skill));
    if (r.how === "template") meta.append(this.el("span", "", "read by a template"));
    if (r.how === "model") meta.append(this.el("span", "", `model, ${Math.round(r.p * 100)}% sure`));
    if (r.unknown?.length) meta.append(this.el("span", "", "new words: " + r.unknown.join(", ")));
    if (r.ran) meta.append(this.el("span", r.ran, r.ran));
    turn.append(meta);
    if (r.chips?.length) {
      const chips = this.el("div", "chips");
      for (const c of r.chips) { const b = this.el("button", "chip", c); b.type = "button"; b.onclick = () => this.say(c); chips.append(b); }
      turn.append(chips);
    }
    this.log.append(turn);
    this.log.scrollTop = this.log.scrollHeight;
  }

  async reset() { await this.post("/api/reset", {}); this.log.replaceChildren(); }
}

customElements.define("termnl-chat", TermNLChat);
