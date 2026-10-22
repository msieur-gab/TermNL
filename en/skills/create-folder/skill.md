---
does: create folder
label: create a folder
admin: no
approve: no
---

## Sentences

- `<create> [me] [a|the] [new] <folder> [(named|called)] {name} [(in|inside|into) [the|my] {place} [<folder>]]`
- `<create> [me] [a|the] [new] <folder> (in|inside) [the|my] {place} [<folder>] [(named|called) {name}]`
- `<create> [me] [a|the] [new] <folder>`

## Values

- name: text, required
- place: @sys.folder, default: home

## Command

mkdir -p {place}/{name}

## Replies

- ask name: What should I call it? | What name should the folder have?
- done: Done, {name} is in {place}. | Created the folder {name} in {place}.
