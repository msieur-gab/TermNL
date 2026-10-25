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

## What it needs

- {name}: a file on the device. If it's missing, ask: Which file? | Which archive should I unpack?
- {place}: a folder on the device. If it's not said: where you are.

## Command

tar -xzf {place}/{name} -C {place}

## Replies

- done: Unpacked {name} in {place}. | {name} is unpacked, in {place}.
