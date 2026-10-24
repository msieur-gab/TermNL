---
does: delete file
label: delete a file
admin: no
approve: yes
---

Goes to the trash (~/.local/share/Trash, as a desktop's trash), so it can be brought back.

## People say

- delete {name} (from/in (the) {place} (folder))
- delete (the) file {name} (from/in (the) {place} (folder))
- delete (a/the) file

## Also said

- delete note.md
- get rid of groceries.md
- throw away report.pdf
- i don't need seed.md anymore, delete it
- erase the file note.md
- can you trash todo.txt for me
- delete a file

## What it needs

- {name}: a file on the device. If it's missing, ask: Which file? | Which file should I delete?
- {place}: a folder on the device. If it's not said: where you are.

## Command

mkdir -p $HOME/.local/share/Trash/files && mv {place}/{name} $HOME/.local/share/Trash/files/

## Replies

- approve: Move {name} from {place} to the trash?
- done: {name} is in the trash. | Done, {name} went to the trash.
