---
does: rename folder
label: rename a folder
admin: no
approve: no
---

A new name never replaces a folder or a file that is already there.

## Sentences

- `<rename> [the|my] [<folder>] {folder} [<folder>] (to|as|into) {new}`
- `<rename> [a|the|this|that] <folder>`

## Values

- folder: @sys.folder, required
- new: text, required, new
- parent: @sys.folder, default: parent of folder

## Command

mv -nT {folder} {parent}/{new}

## Replies

- ask folder: Which folder? | Which folder should I rename?
- ask new: What should it be called? | What's the new name?
- done: Done, {folder} is now {new}. | Renamed the folder {folder} to {new}.
