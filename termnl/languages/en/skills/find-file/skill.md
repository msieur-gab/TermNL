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
- find/search (for) (the/my) {name} file/files
- where are (the/my) {name} files

## Also said

- find note.md
- where is todo.txt
- search for report.pdf
- i can't find groceries.md anywhere
- look for seed.md
- which folder is report.pdf in
- can you track down my todo file
- find a file
- locate scraper.py
- where did I put setup.sh
- can you find the file called website.html
- where's backup.tar.gz
- help me find movie.mkv
- I lost photos.tar.gz somewhere, can you look for it
- find seed.md, I need it for my meeting
- search for the file report.pdf
- search for proton files
- find my invoice files
- where are my seed files
- find the files called report
- search files called notes
- look for files with invoice in the name
- show me every file named backup
- any files named todo in my home

## What it needs

- {name}: a name. If it's missing, ask: What should I look for? | Which file are you looking for?

## Command

find $HOME -iname *{name}*

## Replies

- done: Here's what I found: {output} | I found: {output}
