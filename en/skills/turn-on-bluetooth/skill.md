---
does: turn on bluetooth
label: turn Bluetooth on
admin: yes
approve: no
---

## Sentences

- <turn on> [the] <bluetooth>
- (turn|switch) [the] <bluetooth> [back] on

## Command

rfkill unblock bluetooth

## Replies

- approve: Turn Bluetooth on?
- done: Bluetooth is on. | Done, Bluetooth is on.
