---
does: check memory
label: check memory
reads: memory
admin: no
approve: no
---

## Sentences

- `how much <memory> is (free|left|used|available)`
- `is the <memory> full`
- `<check> [the] <memory>`
- `<memory> [usage]`

## Also said

- how much ram is free
- is my memory full
- how much memory do i have
- ram usage
- memory usage
- am i running out of memory
- how much memory is used

## When it's fine

- You're using {@sys.memory.used} of {@sys.memory.total}. Plenty left.
- {@sys.memory.percent} of the memory is in use: that's fine.

## When it's high

- Memory is getting full: {@sys.memory.used} of {@sys.memory.total} in use. Closing a program or two would help.
- {@sys.memory.percent} of the memory is in use. It still works, but it's getting tight.

## When it's full

- Memory is almost full: only {@sys.memory.free} left. Things may slow down; close a program you don't need.
