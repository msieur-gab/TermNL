---
does: check type
label: look for a kind of file
reads: has
admin: no
approve: no
---

## People say

- is there (a/an/any) {type} (file) (in/inside (the/my) {place} (folder))
- are there (any) {type} (files) (in/inside (the/my) {place} (folder))
- do i have (a/an/any) {type} (files) (in/inside (the/my) {place} (folder))
- check for {type} (files) (in/inside (the/my) {place} (folder))

## Also said

- is there a video in Downloads?
- any images here?
- do I have any PDF somewhere in Documents, even in the subfolders
- tell me if there's a movie anywhere in projects
- is there at least one note in ideas
- check whether Downloads has any pictures in it, subfolders too
- any PDFs in home at all?
- I just want to know if there's a video file somewhere in here or below

## What it needs

- {type}: a file type. If it's missing, ask: Which kind of file? | Looking for images, videos, notes or PDFs?
- {place}: a folder on the device. If it's not said: where you are.

## When it's yes

- Yes, {@sys.has.count} in {place} and its folders:
- Yes: {@sys.has.count} {type} files in {place} and its folders.

## When it's no

- No {type} file in {place} or its folders.
- There's no {type} file in {place}, nor in its folders.
