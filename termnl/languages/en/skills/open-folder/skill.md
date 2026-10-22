---
does: open folder
label: go into a folder
moves: place
reads: folder
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

## Replies

- ask place: Which folder? | Where to?

## When it's fine

- You're in {place} now:
- Now in {place}:

## When it's empty

- You're in {place} now. It's empty.
