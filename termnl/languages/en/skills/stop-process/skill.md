---
does: stop process
label: force a program to stop
admin: no
approve: yes
---

For a program that is stuck. Closing an app normally is close app. Only apps, never the system's own
programs (Gab, 24 Oct, on "kill pipewire": apps only, and say why).

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
- firefox has hung, end it
- can you force the terminal to quit
- the browser froze, kill it please
- terminal is unresponsive
- kill the stuck program
- is there a way to force stop firefox, it's locked up and won't respond
- force kill terminal

## What it needs

- {name}: a running app. If it's missing, ask: Which program? | Which one should I stop?

## Command

pkill -9 -x {name}

## Replies

- unknown name: {name} isn't an app I can stop. Running now:
- approve: Force {name} to stop? Anything not saved in it will be lost.
- done: {name} is stopped. | Stopped {name}.
