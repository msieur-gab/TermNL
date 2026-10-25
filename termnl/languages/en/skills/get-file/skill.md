---
does: get file
label: bring a file from another computer
admin: no
approve: no
---

## People say

- pull {name} from (the/my) {host} (into/to (the/my) {to} (folder))
- pull (a/the) file from (the/my) {host}
- bring over {name} from (the/my) {host}

## Also said

- get report.pdf from the laptop
- grab note.md off the studio pi
- bring scraper.py over from my laptop
- copy movie.mkv from the studio pi onto here
- pull todo.txt from the studio pi to the board
- I left setup.sh on my laptop, can you bring it here
- take website.html from the laptop

## What it needs

- {name}: a name. If it's missing, ask: Which file? | Which file should I bring over?
- {host}: a computer on the network. If it's missing, ask: From which computer? | Which computer is it on?
- {to}: a folder on the device. If it's not said: where you are.

## Command

scp {host}:{name} {to}/

## Replies

- done: {name} is here now, in {to}. | Brought {name} over from {host}, into {to}.
