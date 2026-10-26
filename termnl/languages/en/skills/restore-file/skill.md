---
does: restore file
label: bring a file back from the trash
admin: no
approve: no
topic: Files and folders
---

The other half of delete file: a file moved to the trash (~/.local/share/Trash) comes back where you are,
or into the folder said. A file of the same name already there is never replaced.

## Words

- restore: restore, bring back, recover, undelete, put back, get back

## People say

- restore {name} (to/in/into (the/my) {place} (folder))
- bring {name} back (to/in/into (the/my) {place} (folder))
- get {name} back (from (the/my) "trash")
- restore (a/the) file (from (the/my) "trash")

## Also said

- I deleted notes.md by mistake, get it back
- recover todo.txt from the trash
- put seed.md back
- undelete report.pdf
- can you bring back the file I deleted
- restore a file
- bring back report.pdf from the trash
- can you recover groceries.md
- undo deleting scraper.py
- I binned note.md by accident, restore it to documents
- fish todo.txt out of the trash
- restore website.html into projects, I still need it
- is there a way to get back a file I threw away
- rescue setup.sh from the bin

## What it needs

- {name}: a name. If it's missing, ask: Which file? | Which file should I bring back?
- {place}: a folder on the device. If it's not said: where you are.

## Command

mv -n $HOME/.local/share/Trash/files/{name} {place}/

## Replies

- done: {name} is back, in {place}. | Done, {name} is back in {place}.
