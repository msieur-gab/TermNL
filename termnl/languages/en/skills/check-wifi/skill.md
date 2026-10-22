---
does: check wifi
label: check Wi-Fi
admin: no
approve: no
---

## Sentences

- `is [the] <wifi> (on|off|working)`
- `(which|what) <wifi> [network] am i (on|connected to)`
- `<check> [the] <wifi>`

## Command

nmcli -t -f active,ssid dev wifi

## Replies

- done: Wi-Fi: {output} | Here's the Wi-Fi: {output}
