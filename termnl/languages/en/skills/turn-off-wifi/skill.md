---
does: turn off wifi
label: turn Wi-Fi off
admin: yes
approve: yes
---

## Sentences

- `<turn off> [the] <wifi>`
- `(turn|switch) [the] <wifi> off`

## Command

iw dev | grep -o 'Interface .*' | cut -d' ' -f2 | xargs -I@ ip link set @ down

## Replies

- approve: Turn Wi-Fi off? If you're reaching me over Wi-Fi, we'll lose the connection.
- done: Wi-Fi is off. | Done, Wi-Fi is off.
