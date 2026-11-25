// Small DOM helpers the demo's scripts share.

export const $ = id => document.getElementById(id);

// an element with a class and its text: el("div", "say", "Hello")
export function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

// a button that says a sentence when tapped
export function sayButton(cls, text, say) {
  const b = el("button", cls, text);
  b.type = "button";
  b.onclick = () => say(text);
  return b;
}
