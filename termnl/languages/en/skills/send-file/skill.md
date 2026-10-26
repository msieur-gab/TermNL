---
does: send file
label: send a file to another computer
admin: no
approve: yes
---

## People say

- send (the/my) {name} (file) to (the/my) {host}
- send (the/my) {name} (file) from (the/my) {place} (folder) to (the/my) {host}
- send (a/the) file to (the/my) {host}
- send (a/the) file to another computer

## Also said

- send report.pdf to the laptop
- push scraper.py to my laptop
- put a copy of note.md on the studio pi
- transfer backup.tar.gz to the laptop please
- can you give the laptop a copy of todo.txt
- send setup.sh to studio pi
- I want website.html on my laptop, send it over the network
- send groceries.md to the laptop
- can you send movie.mkv from Downloads to the studio pi
- ship seed.md over to the studio pi
- beam website.html to my laptop
- I'd like to send report.pdf from Documents to my laptop
- send note.md to the laptop so I can edit it there
- send photos.tar.gz to studio-pi, I need it on the other board
- to the laptop, send todo.txt

## What it needs

- {name}: a file on the device. If it's missing, ask: Which file? | Which file should I send?
- {place}: a folder on the device. If it's not said: where you are.
- {host}: a computer on the network. If it's missing, ask: To which computer? | Where should I send it?

## Command

scp {place}/{name} {host}:

## Replies

- approve: Send {name} to {host}? It lands in {host}'s home folder.
- done: {name} is on {host} now, in its home folder. | Sent {name} to {host}.
