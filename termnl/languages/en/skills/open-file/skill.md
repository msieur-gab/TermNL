---
does: open file
label: open a file
admin: no
approve: no
---

## Sentences

- `<open> [the|my] {name} [<file>] [(in|inside|from) [the|my] {place} [<folder>]]`
- `<open> [the|my] {name} [<file>] (located|that is|which is) (in|inside) [the|my] {place} [<folder>]`
- `<open> [a|the|my|this|that] <file>`

## Values

- name: @sys.file, required
- place: @sys.folder, default: here

## Command

xdg-open {place}/{name}

## Replies

- ask name: Which file? | Which file should I open?
- done: Opening {name} from {place}. | {name} is opening.
