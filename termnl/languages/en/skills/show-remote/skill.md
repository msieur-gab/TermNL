---
does: show remote
label: show what's on another computer
admin: no
approve: no
---

## People say

- show (me) what's on (the/my) {host}
- show (me) the files on (the/my) {host}
- show (me) (the) remote computer {host}
- show (a/the) remote computer

## Also said

- what's on the laptop?
- show the files on the studio pi
- list what my laptop has
- what can you see on the laptop over the network
- what files are on my laptop right now
- I'd like to look at what's stored on the studio pi

## What it needs

- {host}: a computer on the network. If it's missing, ask: Which computer? | Which computer should I look at?

## Command

ssh {host} ls -p

## Replies

- done: On {host}: {output} | {host}'s home folder holds: {output}
