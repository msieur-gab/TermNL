---
does: show wifi
label: show Wi-Fi networks
reads: networks
admin: no
approve: no
---

## Sentences

- `(which|what) <wifi> networks are (there|around|available)`
- `(which|what) networks are (there|around|available)`
- `<show> [me] [the|available] <wifi> networks`

## Command

nmcli -t -f in-use,ssid,signal dev wifi list

## When it's fine

- I can see {@sys.networks.count} networks; the strongest is {@sys.networks.best}:
- {@sys.networks.count} networks around, strongest first:

## When it's none

- I can't see any Wi-Fi network. Wi-Fi may be off.
