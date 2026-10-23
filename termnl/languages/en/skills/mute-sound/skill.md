---
does: mute sound
label: mute the sound
admin: no
approve: no
---

## Sentences

- `<mute> [the|my] [<sound>|<music>]`

## Command

pactl set-sink-mute @DEFAULT_SINK@ 1

## Replies

- done: Muted. | The sound is off.
