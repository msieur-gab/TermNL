---
does: download file
label: download a file
admin: no
approve: no
---

## People say

- download {link} (to/into (the/my) {place} (folder))
- download (the) file (from) {link}
- download (a) file

## Also said

- download https://example.org/file.pdf
- get the file at https://example.org/report.pdf
- save https://example.org/file.pdf to downloads
- download a file
- grab this link https://example.org/notes.txt
- fetch https://example.org/file.pdf for me
- i need the pdf from https://example.org/file.pdf
- pull down https://example.org/music.zip
- could you grab https://example.com/report.pdf and put it in documents
- save the file from https://example.com/photos.zip
- I'd like to download https://example.com/setup.sh into projects
- fetch https://example.com/music.zip into downloads, I need it for tonight
- can you get https://example.com/data.csv from the internet for me
- is there a way to download https://example.com/file.zip to home
- download https://example.com/notes.zip

## What it needs

- {link}: a web address. If it's missing, ask: What's the address? | Which web address?
- {place}: a folder on the device. If it's not said: downloads.

## Command

wget -P {place} {link}

## Replies

- done: Downloaded into {place}. | It's in {place}.
