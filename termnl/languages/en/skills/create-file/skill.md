---
does: create file
label: create a file
admin: no
approve: no
---

## Sentences

- `<create> [me] [a|an|the] [new] [{type}] <file> [(named|called|call|name|titled)] {name} [(in|inside|into) [the|my] {place} [<folder>]]`
- `<create> [me] [a|an|the] [new] [{type}] <file> (in|inside) [the|my] {place} [<folder>] [(named|called|call|name|titled) {name}]`
- `<create> [me] [a|an|the] [new] [{type}] <file>`

## Also said

- create a file
- make a new file
- new file note.md
- create todo.txt
- start a file called groceries.md
- make an empty file named seed.md
- i need a new text file
- add a file called note.md in documents

## Values

- name: text, required, new
- type: filetype, default: markdown
- place: @sys.folder, default: here

## Command

touch {place}/{name}

## Replies

- ask name: What should I call it? | What name should the file have?
- done: Done, {name} is in {place}. | Created {name} in {place}.
