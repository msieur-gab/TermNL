---
does: ping remote
label: check another computer answers
admin: no
approve: no
---

Born as a test of dropping a skill in (FRAMES.md): "ping" is in no list of words/; this folder brings it.

## Words

- ping: ping, reach

## People say

- ping (the/my) {host}
- can you reach (the/my) {host}
- ping (a/the) remote computer

## Also said

- ping the laptop
- is the studio pi reachable
- can the board reach my laptop
- does the laptop answer

## What it needs

- {host}: a computer on the network. If it's missing, ask: Which computer? | Which computer should I ping?

## Command

ping -c 3 {host}

## Replies

- done: {host} answers: {output}
