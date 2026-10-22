---
does: create file
label: create a file
admin: no
approve: no
---

## Sentences

- <create> [a|an|the] [new] [{type}] <file> [(named|called)] {name} [(in|inside|into) [the|my] {place} [<folder>]]
- <create> [a|an|the] [new] [{type}] <file> (in|inside) [the|my] {place} [<folder>] [(named|called) {name}]
- <create> [a|an|the] [new] [{type}] <file>
- <create> {name} [(in|inside|into) [the|my] {place} [<folder>]]

## Values

- name: text, required
- type: filetype, default: markdown
- place: @sys.folder, default: home

## Command

touch {place}/{name}

## Replies

- ask name: What should I call it? | What name should the file have?
- done: Done, {name} is in {place}. | Created {name} in {place}.
