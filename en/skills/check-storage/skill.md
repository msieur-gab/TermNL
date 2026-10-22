---
does: check storage
label: check storage
admin: no
approve: no
---

## Sentences

- how much (space|storage|disk space) [is] (left|free|available)
- how much (space|storage) do i have [left]
- is the <storage> full
- am i running out of <storage>
- <check> [the] <storage>
- <storage> [usage|left]

## Command

df -h /

## Replies

- done: Storage: {output} | Here's the space: {output}
