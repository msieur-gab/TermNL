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
- browse the files on my laptop
- can you show me what's on the studio pi
- laptop files
- I'd like to see what the studio pi has on it
- is there a way to look at my laptop's files from here
- list the files over on the studio pi
- I left something on the laptop, show me what's there
- show me the studio pi's files, I can't remember what I put there

## What it needs

- {host}: a computer on the network. If it's missing, ask: Which computer? | Which computer should I look at?

## Command

ssh {host} ls -p

## Replies

- done: On {host}: {output} | {host}'s home folder holds: {output}
