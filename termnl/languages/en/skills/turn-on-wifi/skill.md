---
does: turn on wifi
label: turn Wi-Fi on
admin: yes
approve: no
---

## People say

- turn on (the) wifi
- turn/switch (the) wifi (back) on

## Also said

- wifi on
- switch on the wireless
- enable wifi
- bring the wifi back
- start the wifi
- i need wifi again
- put the wifi back on please

## Command

iw dev | grep -o 'Interface .*' | cut -d' ' -f2 | xargs -I@ ip link set @ up

## Replies

- approve: Turn Wi-Fi on? | Shall I switch Wi-Fi on?
- done: Wi-Fi is on. | Done, Wi-Fi is back on.
