---
does: copy file
label: copy a file
admin: no
approve: no
---

## People say

- copy {name} (from (the) {place} (folder)) to/into (the/my) {to} (folder)
- copy (the) file {name} to/into (the/my) {to} (folder)
- make a copy of {name} in (the/my) {to} (folder)
- copy (a/the) file

## Also said

- copy note.md
- make a copy of report.pdf
- duplicate todo.txt
- copy groceries.md into documents
- i want a second copy of seed.md in projects
- put a copy of report.pdf in downloads but keep the original
- can you back up note.md to the ideas folder
- copy a file

## What it needs

- {name}: a file on the device. If it's missing, ask: Which file? | Which file should I copy?
- {place}: a folder on the device. If it's not said: where you are.
- {to}: a folder on the device. If it's missing, ask: Where should the copy go? | Into which folder?

## Command

cp {place}/{name} {to}/

## Replies

- done: There's a copy of {name} in {to}. | Copied {name} to {to}.
