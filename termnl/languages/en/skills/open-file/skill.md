---
does: open file
label: open a file
admin: no
approve: no
---

## People say

- open (the/my) {name} (file) (in/inside/from (the/my) {place} (folder))
- open (the/my) {name} (file) located in/inside (the/my) {place} (folder)
- open (the/my) {name} (file) that is in/inside (the/my) {place} (folder)
- open (the/my) {name} (file) which is in/inside (the/my) {place} (folder)
- open (a/the/my/this/that) file

## Also said

- open a file
- show me todo.txt
- open report.pdf
- let me read groceries.md
- open the file seed.md
- can you open my todo file
- view report.pdf
- can you pull up report.pdf
- bring up todo.txt for me
- i'd like to open groceries.md from Documents
- open scraper.py in the projects folder
- i need to check the layout, open website.html in projects
- i want to edit my list, open todo.txt
- open seed.md

## What it needs

- {name}: a file on the device. If it's missing, ask: Which file? | Which file should I open?
- {place}: a folder on the device. If it's not said: where you are.

## Command

xdg-open {place}/{name}

## Replies

- done: Opening {name} from {place}. | {name} is opening.
