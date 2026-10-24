---
does: rename folder
label: rename a folder
admin: no
approve: no
---

A new name never replaces a folder or a file that is already there.

## People say

- rename (the/my) (folder) {folder} (folder) to/as/into {new}
- rename (a/the/this/that) folder

## Also said

- rename a folder
- rename the ideas folder to projects
- change the name of the downloads folder
- give the projects folder a new name
- the ideas folder needs another name
- rename folder documents
- call the ideas folder projects instead
- i want to rename a directory

## What it needs

- {folder}: a folder on the device. If it's missing, ask: Which folder? | Which folder should I rename?
- {new}: a new name. If it's missing, ask: What should it be called? | What's the new name?
- {parent}: a folder on the device. If it's not said: the folder {folder} is in.

## Command

mv -nT {folder} {parent}/{new}

## Replies

- done: Done, {folder} is now {new}. | Renamed the folder {folder} to {new}.
