---
does: move file
label: move a file
admin: no
approve: no
---

## People say

- move {name} (from (the) {place} (folder)) to/into (the/my) {to} (folder)
- move (the) file {name} to/into (the/my) {to} (folder)
- move (a/the) file

## Also said

- move note.md to documents
- put todo.txt in the projects folder
- move a file
- can you take report.pdf out of downloads and put it in documents
- shift groceries.md over to home
- i want seed.md in ideas instead of here
- relocate todo.txt to projects
- send note.md into the ideas folder

## What it needs

- {name}: a file on the device. If it's missing, ask: Which file? | Which file should I move?
- {place}: a folder on the device. If it's not said: where you are.
- {to}: a folder on the device. If it's missing, ask: Where should it go? | Into which folder?

## Command

mv {place}/{name} {to}/

## Replies

- done: {name} is now in {to}. | Moved {name} to {to}.
