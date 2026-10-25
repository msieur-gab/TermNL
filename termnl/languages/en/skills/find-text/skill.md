---
does: find text
label: find which files mention something
admin: no
approve: no
topic: Files and folders
---

Looks inside the files, not at their names (find file does names): every text file under the folder, home if
none is said, that mentions the words, whatever their capitals.

## Words

- text: text, words, phrase

## People say

- find (the) text {words} (in (the/my) {place} (folder))
- which/what notes/files mention {words} (in (the/my) {place} (folder))
- search (in) (the/my) notes/files for {words}
- where did I write (about) {words}
- find (some) text

## Also said

- which of my notes talk about wifi
- do I have notes about the board
- look through my files for permacomputing
- anything about wifi in my notes
- what's in my notes about bluetooth
- which files say hello

## What it needs

- {words}: a name. If it's missing, ask: What should I look for? | Which words should I look for?
- {place}: a folder on the device. If it's not said: home.

## Command

grep -rIil -- {words} {place} || true

## Replies

- done: Mentioned in: {output} | These mention {words}: {output}
