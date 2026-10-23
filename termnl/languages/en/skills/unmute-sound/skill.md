---
does: unmute sound
label: unmute the sound
admin: no
approve: no
---

## Sentences

- `<unmute> [the|my] [<sound>|<music>]`
- `turn [the] <sound> back on`

## Command

pactl set-sink-mute @DEFAULT_SINK@ 0

## Replies

- done: The sound is back. | Unmuted.
