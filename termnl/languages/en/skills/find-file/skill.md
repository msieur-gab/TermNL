---
does: find file
label: find a file
admin: no
approve: no
---

## People say

- find (the/my) (file) {name}
- where is (the/my) (file) {name}
- where's (the/my) (file) {name}
- find (a) file

## Also said

- find note.md
- where is todo.txt
- search for report.pdf
- i can't find groceries.md anywhere
- look for seed.md
- which folder is report.pdf in
- can you track down my todo file
- find a file

## What it needs

- {name}: a name. If it's missing, ask: What should I look for? | Which file are you looking for?

## Command

find $HOME -iname *{name}*

## Replies

- done: Here's what I found: {output} | I found: {output}
