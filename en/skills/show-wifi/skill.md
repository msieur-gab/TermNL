---
does: show wifi
label: show Wi-Fi networks
admin: no
approve: no
---

## Sentences

- (which|what) <wifi> networks are (there|around|available)
- (which|what) networks are (there|around|available)
- <show> [me] [the|available] <wifi> networks

## Command

nmcli -t -f ssid,signal dev wifi list

## Replies

- done: Networks around: {output} | I can see: {output}
