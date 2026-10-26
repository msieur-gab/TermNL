---
does: create folder
label: create a folder
admin: no
approve: no
---

## People say

- create (me) (a/the) ("new") folder (named/called/call/name/titled) {name} (in/inside/into (the/my) {place} (folder))
- create (me) (a/the) ("new") folder in/inside (the/my) {place} (folder) (named/called/call/name/titled {name})
- create (me) (a/the) ("new") folder
- create (me) (a/the) ("new") {name} folder (in/inside/into (the/my) {place} (folder))

## Also said

- create a folder
- make a new folder
- new folder
- make a folder named ideas in documents
- add a folder called projects
- create a directory
- i need a new folder in downloads
- mkdir ideas
- make a directory called notes
- can you set up a new folder named drafts in projects
- new folder in ideas
- I'd like a folder called sketches inside documents
- is there a way to add a folder named archive in downloads
- start a new folder called recipes
- I need somewhere to keep my drafts, make a folder called drafts
- make a folder named photos in home so I can sort my pictures

## What it needs

- {name}: a new name. If it's missing, ask: What should I call it? | What name should the folder have?
- {place}: a folder on the device. If it's not said: where you are.

## Command

mkdir -p {place}/{name}

## Replies

- done: Done, {name} is in {place}. | Created the folder {name} in {place}.
