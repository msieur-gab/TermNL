---
does: compress file
label: compress a file
admin: no
approve: no
---

## People say

- compress (the/my) {name} (file) (in/inside/from (the/my) {place} (folder))
- compress (the) file {name}
- compress (a/the) file

## Also said

- compress movie.mkv
- zip up report.pdf
- make an archive of scraper.py
- can you pack setup.sh into a tar.gz next to it
- shrink website.html into an archive
- turn note.md into a compressed file
- archive just the report
- I need movie.mkv squeezed into a single archive beside the original

## What it needs

- {name}: a file on the device. If it's missing, ask: Which file? | Which file should I compress?
- {place}: a folder on the device. If it's not said: where you are.

## Command

tar -czf {place}/{name}.tar.gz -C {place} {name}

## Replies

- done: {name} is compressed, beside it. | Done: a compressed copy of {name} is next to it.
