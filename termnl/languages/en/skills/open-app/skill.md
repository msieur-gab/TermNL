---
does: open app
label: open an app
admin: no
approve: no
---

## Sentences

- `<open> [the|a|my] {name} [<app>]`
- `<open> [an|a] <app>`

## Values

- name: @sys.app, required

## Command

setsid {name}

## Replies

- ask name: Which app? | Which one should I open?
- done: Opening {name}. | {name} is opening.
