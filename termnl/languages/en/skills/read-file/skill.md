---
does: read file
label: read a file
admin: no
approve: no
---

## People say

- read (me) (the/my) {name} (file) (in/inside/from (the/my) {place} (folder))
- what does (the/my) {name} (file) say
- read (a/the) file

## Also said

- read me note.md
- show the first lines of groceries.md
- what's written in seed.md
- let me see the text inside setup.sh
- can you print the beginning of website.html for me
- read todo.txt
- I want to see what my grocery list says

## What it needs

- {name}: a file on the device. If it's missing, ask: Which file? | Which file should I read?
- {place}: a folder on the device. If it's not said: where you are.

## Command

head -n 40 {place}/{name}

## Replies

- done: {name} says: {output} | Here's {name}: {output}
