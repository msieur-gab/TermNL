---
does: stop process
label: force a program to stop
admin: no
approve: yes
---

For a program that is stuck. Closing an app normally is close app.

## People say

- stop {name}
- force quit {name}
- stop (the) process {name}
- {name} is frozen/stuck
- stop (a/the) process

## Also said

- firefox is frozen, force it to stop
- the browser is stuck
- force quit the terminal
- firefox won't close, make it stop
- the terminal is not responding
- end that stuck program
- force a program to stop

## What it needs

- {name}: a running app. If it's missing, ask: Which program? | Which one should I stop?

## Command

pkill -9 -x {name}

## Replies

- approve: Force {name} to stop? Anything not saved in it will be lost.
- done: {name} is stopped. | Stopped {name}.
