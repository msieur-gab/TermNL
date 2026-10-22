---
does: rename file
label: rename a file
admin: no
approve: no
---

Gab, 22 Oct: "perhaps we will need a rename file/folder skill". A new name never replaces a file
that is already there; a new name without an extension keeps the old one's (notes.md → ideas.md).

## Sentences

- `<rename> [the|my] [<file>] {name} [<file>] (to|as|into) {new}`
- `<rename> [the|my] [<file>] {name} [<file>] (in|inside) [the|my] {place} [<folder>] (to|as|into) {new}`
- `<rename> [a|the|this|that] <file>`

## Values

- name: @sys.file, required
- place: @sys.folder, default: here
- new: text, required, new

## Command

mv -nT {place}/{name} {place}/{new}

## Replies

- ask name: Which file? | Which file should I rename?
- ask new: What should it be called? | What's the new name?
- done: Done, {name} is now {new}. | Renamed {name} to {new}.
