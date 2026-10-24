---
does: rename file
label: rename a file
admin: no
approve: no
---

Gab, 22 Oct: "perhaps we will need a rename file/folder skill". A new name never replaces a file
that is already there; a new name without an extension keeps the old one's (notes.md → ideas.md).

## People say

- rename (the/my) (file) {name} (file) to/as/into {new}
- rename (the/my) (file) {name} (file) in/inside (the/my) {place} (folder) to/as/into {new}
- rename (a/the/this/that) file

## Also said

- rename a file
- rename note.md to seed.md
- change the name of todo.txt
- call groceries.md something else
- give report.pdf a new name
- i want to rename seed.md
- todo.txt needs a new name
- rename this file

## What it needs

- {name}: a file on the device. If it's missing, ask: Which file? | Which file should I rename?
- {place}: a folder on the device. If it's not said: where you are.
- {new}: a new name. If it's missing, ask: What should it be called? | What's the new name?

## Command

mv -nT {place}/{name} {place}/{new}

## Replies

- done: Done, {name} is now {new}. | Renamed {name} to {new}.
