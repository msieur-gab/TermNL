---
does: restart system
label: restart the board
admin: yes
approve: no
---

## Sentences

- `<restart> [the] <system>`

## Command

systemctl reboot

## Replies

- approve: Restart the board now? | Restart now? I'll be back in a minute or two.
- done: Restarting. | See you in a minute.
