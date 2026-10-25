---
does: show size
label: show what takes the most space
admin: no
approve: no
---

The biggest files and folders in a folder, biggest first (check size gives one folder's total; check storage,
the disk's). Where you are, if no folder is said.

## People say

- what takes (up) the most space (in (the/my) {place} (folder))
- show (me) the biggest files/folders (in (the/my) {place} (folder))
- what is the biggest (thing) (in (the/my) {place} (folder))
- what are the biggest things (in (the/my) {place} (folder))
- show (me) the biggest files/folders here
- what takes (up) the most space here

## Also said

- what's eating my space in Downloads
- which folders are the heaviest
- show me what's huge in home
- what is filling up the projects folder
- list the largest files here

## What it needs

- {place}: a folder on the device. If it's not said: where you are.

## Command

du -ah -d 1 {place} | sort -rh | head -n 9

## Replies

- done: The biggest in {place}, biggest first: {output} | In {place}: {output}
