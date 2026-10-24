---
does: delete folder
label: delete a folder
admin: no
approve: yes
---

Goes to the trash (~/.local/share/Trash), so it can be brought back.

## People say

- delete (the/my) {name} folder
- delete (the) folder {name}
- delete (a/the) folder

## Also said

- remove the projects folder
- delete a folder
- i don't need the ideas directory anymore
- wipe out the projects folder
- can you remove that whole folder
- throw away the ideas folder

## What it needs

- {name}: a folder on the device. If it's missing, ask: Which folder? | Which folder should I delete?

## Command

mkdir -p $HOME/.local/share/Trash/files && mv {name} $HOME/.local/share/Trash/files/

## Replies

- approve: Move the folder {name} and everything in it to the trash?
- done: {name} is in the trash. | Done, the folder {name} went to the trash.
