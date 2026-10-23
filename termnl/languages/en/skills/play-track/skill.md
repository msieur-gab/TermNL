---
does: play track
label: play an artist, album or song
admin: no
approve: no
---

Gab, 23 Oct: "say play daft punk or play a thousand leaves". The names are the Music folder's: its artists, albums and titles.

## Sentences

- `<play> [the] [<track>] {name}`
- `<play> [some|the|something] [<music>|<track>] (by|from) {name}`
- `(i want|i'd like) [to] (hear|listen to) {name}`

## Values

- name: @sys.music, required

## Command

mpc searchplay any {name}

## Replies

- ask name: What should I play? | Which artist, album or song?
- done: Playing {name}. | Here's {name}.
