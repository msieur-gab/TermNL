---
does: install app
label: install a program
admin: yes
approve: yes
---

## People say

- install {name}
- install (the) app/program {name}
- install (a/an) (new) app/program

## Also said

- get gimp
- put git on the board
- i need vlc, can you install it
- add the gimp program
- install a program
- set up git for me

## What it needs

- {name}: a program name. If it's missing, ask: Which program? | What should I install?

## Command

apt-get install -y {name}

## Replies

- approve: Install {name}? It downloads it and adds it to the system.
- done: {name} is installed. | Done, {name} is installed.
