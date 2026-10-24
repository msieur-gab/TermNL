---
does: close app
label: close an app
admin: no
approve: yes
---

Gab's log, 22 Oct: "close expressvpn". Approved first: anything not saved in the app is lost.

## Sentences

- `<close> [the|my] {name} [<app>]`
- `<close> [an|a|the] <app>`

## Also said

- close an app
- exit firefox
- shut the browser
- i am done with the terminal, close it
- get out of firefox

## Values

- name: @sys.running, required

## Command

pkill -x {name}

## Replies

- ask name: Which app? | Which one should I close?
- approve: Close {name}? Anything not saved in it will be lost.
- done: {name} is closed. | Closed {name}.
