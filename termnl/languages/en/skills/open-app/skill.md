---
does: open app
label: open an app
admin: no
approve: no
---

## Sentences

- `<open> [the|a|my] {name} [<app>]`
- `<open> [an|a] <app>`

## Also said

- open an app
- start the browser
- launch the terminal
- i want to browse the web
- open a terminal
- start firefox please
- run the browser

## Values

- name: @sys.app, required

## Command

setsid {name}

## Replies

- ask name: Which app? | Which one should I open?
- done: Opening {name}. | {name} is opening.
