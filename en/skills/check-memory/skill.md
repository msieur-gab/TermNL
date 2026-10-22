---
does: check memory
label: check memory
admin: no
approve: no
---

## Sentences

- how much <memory> is (free|left|used|available)
- is the <memory> full
- <check> [the] <memory>
- <memory> [usage]

## Command

free -h

## Replies

- done: Memory: {output} | Here's the memory: {output}
