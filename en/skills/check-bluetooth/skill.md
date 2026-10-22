---
does: check bluetooth
label: check Bluetooth
admin: no
approve: no
---

## Sentences

- is [the] <bluetooth> (on|off|working)
- <check> [the] <bluetooth>

## Command

bluetoothctl show

## Replies

- done: Bluetooth: {output}
