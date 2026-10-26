---
does: create file
label: create a file
admin: no
approve: no
---

## People say

- create (me) (a/an/the) ("new") ({type}) file (named/called/call/name/titled) {name} (in/inside/into (the/my) {place} (folder))
- create (me) (a/an/the) ("new") ({type}) file in/inside (the/my) {place} (folder) (named/called/call/name/titled {name})
- create (me) (a/an/the) ("new") ({type}) file

## Also said

- create a file
- make a new file
- new file note.md
- create todo.txt
- start a file called groceries.md
- make an empty file named seed.md
- i need a new text file
- add a file called note.md in documents
- make me a new markdown file called plan.md
- can you create a text file named shopping.txt in documents
- start a fresh note called journal.md
- I'd like a blank file in projects called index.html
- new file please
- touch draft.md
- create a file called meeting.md in ideas, I want to jot down notes from today
- is there a way to make an empty python file named test.py in projects so I can start coding

## What it needs

- {name}: a new name. If it's missing, ask: What should I call it? | What name should the file have?
- {type}: a file type. If it's not said: markdown.
- {place}: a folder on the device. If it's not said: where you are.

## Command

touch {place}/{name}

## Replies

- done: Done, {name} is in {place}. | Created {name} in {place}.
