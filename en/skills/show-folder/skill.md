---
does: show folder
label: show a folder
admin: no
approve: no
---

## Sentences

- `<show> [me] [the|my] {place} [<folder>]`
- `(what's|what is) in [the|my] {place} [<folder>]`

## Values

- place: @sys.folder, default: here

## Command

ls {place}

## Replies

- done: In {place}: {output}
