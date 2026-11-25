// The desk's line icons (symbios, web/js/icons.js): one line in the text's colour, so they follow the page.

const svg = d => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;

export const I = {
  folder: svg(`<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>`),
  note: svg(`<path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5M9 13h7M9 17h5"/>`),
  picture: svg(`<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="m21 17-5-5-9 8"/>`),
  video: svg(`<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M10 9l5 3-5 3z"/>`),
  track: svg(`<path d="M9 18V5l10-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="16" cy="16" r="3"/>`),
  document: svg(`<path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5"/><path d="M9 14h6M9 17h4"/>`),
  file: svg(`<path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5"/>`),
  terminal: svg(`<rect x="3" y="4" width="18" height="16" rx="2"/><path d="m7 9 3 3-3 3M13 15h4"/>`),
  lock: svg(`<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>`),
  panel: svg(`<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M15 4v16"/>`),
};

// a file's icon, by its extension; a folder's by its kind
const KINDS = [[/\.(md|txt)$/i, "note"], [/\.(jpe?g|png|gif|webp|svg)$/i, "picture"], [/\.(mp4|mkv|webm|mov|avi)$/i, "video"],
  [/\.(mp3|flac|ogg|wav|m4a)$/i, "track"], [/\.(pdf|docx?|odt)$/i, "document"], [/\.(sh|py|js|html?|css)$/i, "terminal"]];

export function iconOf(name, kind) {
  if (kind === "folder" || /\/$/.test(name)) return I.folder;
  return I[(KINDS.find(([re]) => re.test(name)) || [null, "file"])[1]];
}
