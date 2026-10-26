---
does: unpack file
label: unpack an archive
admin: no
approve: no
---

## People say

- unpack (the/my) {name} (file) (in/inside/from (the/my) {place} (folder))
- unpack (a/an/the) file

## Also said

- extract backup.tar.gz
- unzip backup.tar.gz right where it is
- can you decompress photos.tar.gz for me
- untar photos.tar.gz
- I downloaded backup.tar.gz, please unpack it in place
- can you extract backup.tar.gz in home
- unpack the archive photos.tar.gz in Downloads
- i'd like to unzip photos.tar.gz
- is there a way to decompress backup.tar.gz here
- i need the pictures inside, so extract photos.tar.gz
- i want my old files back, unpack backup.tar.gz
- untar backup.tar.gz

## What it needs

- {name}: a file on the device. If it's missing, ask: Which file? | Which archive should I unpack?
- {place}: a folder on the device. If it's not said: where you are.

## Command

tar -xzf {place}/{name} -C {place}

## Replies

- done: Unpacked {name} in {place}. | {name} is unpacked, in {place}.
