---
does: show folder
label: show a folder
reads: folder
admin: no
approve: no
---

## Sentences

- `<show> [me] [the|my] {place} [<folder>]`
- `(what's|what is) in [the|my] {place} [<folder>]`
- `(what's|what is) (here|in here|in this <folder>)`
- `what do i have (in|inside) [the|my] {place} [<folder>]`
- `what do i have here`
- `ls [[the|my] {place} [<folder>]]`
- `<show> [me] [all] [the|my] (<file>|<folder>|things) [(in|inside|of) [the|my] {place} [<folder>]]`
- `(what|which) <file> (are|do i have) [(here|in [the|my] {place} [<folder>])]`

## Values

- place: @sys.folder, default: here

## When it's fine

- In {place}:
- Here's what {place} holds:

## When it's empty

- {place} is empty.
- There's nothing in {place} yet.
