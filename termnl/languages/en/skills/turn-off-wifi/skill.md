---
does: turn off wifi
label: turn Wi-Fi off
admin: yes
approve: yes
---

## Words

- stop, kill, cut, shut off, disconnect, close → turn off

## People say

- turn off (the) wifi
- turn/switch (the) wifi off

## Also said

- cut the wireless
- switch the wifi off
- no more wifi
- wifi off
- kill the wireless
- disable wifi
- get rid of the wifi for now
- shut off the wireless
- disconnect the wifi
- i don't want wifi right now
- the wifi can go off now
- switch off the wifi
- can you turn the wifi off
- wifi off please
- I'd like the wireless switched off
- is there a way to shut the wifi down
- power down the wifi
- I'm on ethernet now, turn off the wifi
- turn off the wireless to save power

## Command

iw dev | grep -o 'Interface .*' | cut -d' ' -f2 | xargs -I@ ip link set @ down

## Replies

- approve: Turn Wi-Fi off? If you're reaching me over Wi-Fi, we'll lose the connection.
- done: Wi-Fi is off. | Done, Wi-Fi is off.
