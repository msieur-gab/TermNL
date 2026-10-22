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

- place: @sys.folder, required

## Command

ls {place}

## Replies

- ask place: Which folder?
- done: In {place}: {output}
