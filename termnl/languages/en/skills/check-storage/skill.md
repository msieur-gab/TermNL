---
does: check storage
label: check storage
reads: storage
admin: no
approve: no
---

## Sentences

- `how much (space|storage|disk space) [is] (left|free|available)`
- `how much (space|storage) do i have [left]`
- `is the <storage> full`
- `am i running out of <storage>`
- `<check> [the] <storage>`
- `<storage> [usage|left]`

## When it's fine

- You have {@sys.storage.free} free on the main disk, out of {@sys.storage.total}.
- Plenty of room: {@sys.storage.free} free.

## When it's filling up

- The disk is filling up: {@sys.storage.free} left of {@sys.storage.total}.

## When it's full

- The disk is almost full: only {@sys.storage.free} left. Some things may stop working until you make room.
