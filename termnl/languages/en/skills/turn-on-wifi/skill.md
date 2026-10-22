---
does: turn on wifi
label: turn Wi-Fi on
admin: yes
approve: no
---

## Sentences

- `<turn on> [the] <wifi>`
- `(turn|switch) [the] <wifi> [back] on`

## Command

nmcli radio wifi on

## Replies

- approve: Turn Wi-Fi on? | Shall I switch Wi-Fi on?
- done: Wi-Fi is on. | Done, Wi-Fi is back on.
