---
does: compress folder
label: compress a folder
admin: no
approve: no
---

## People say

- compress (the/my) {name} (folder)
- compress (the) folder {name}
- make a zip of (the/my) {name} (folder)
- compress (a/the) folder

## Also said

- compress the projects folder
- zip ideas
- make a zip of documents
- shrink the downloads folder
- pack the projects folder into one file
- i want an archive of the ideas folder
- can you zip up my documents
- compress a folder
- zip up the downloads folder
- can you make an archive of my projects folder
- zip the ideas folder
- I'd like the documents folder squeezed into a zip
- is there a way to pack the home folder into an archive
- bundle the projects folder into a zip file
- I want to send the ideas folder to a friend, zip it up first
- zip up documents so I can back it up

## What it needs

- {name}: a folder on the device. If it's missing, ask: Which folder? | Which folder should I compress?

## Command

tar -czf {name}.tar.gz {name}

## Replies

- done: {name} is compressed, beside it. | Done: a compressed copy of {name} is next to it.
