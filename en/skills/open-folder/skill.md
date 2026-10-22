---
does: open folder
label: go into a folder
moves: place
admin: no
approve: no
---

## Sentences

- `<open> [the|my] {place} [<folder>]`
- `go (to|into|inside) [the|my] {place} [<folder>]`
- `(cd|enter) [the|my] {place} [<folder>]`
- `<open> [a|the|my] <folder>`

## Values

- place: @sys.folder, required

## Command

ls {place}

## Replies

- ask place: Which folder? | Where to?
- done: You're in {place} now. {output} | Now in {place}. {output}
