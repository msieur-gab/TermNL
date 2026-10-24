---
does: check wifi
label: check Wi-Fi
reads: wifi
admin: no
approve: no
---

## Sentences

- `is [the] <wifi> (on|off|working)`
- `(which|what) (<wifi> [network]|network) am i (on|connected to)`
- `<check> [the] <wifi>`

## Also said

- am i on wifi
- which wifi am i on
- is the wireless connected
- wifi status
- how strong is the wifi signal
- is the wifi ok
- check the wifi
- wifi check
- how good is my wifi signal
- what is the name of the wifi i am on
- is the wifi still connected
- tell me about my wifi connection

## Command

iw dev | grep -o 'Interface .*' | cut -d' ' -f2 | xargs -I@ sh -c 'iw dev @ link; iw dev @ scan dump' | grep -E '^(Connected|Not connected|BSS)|SSID: |signal: '

## When it's fine

- You're on {@sys.wifi}, with a good signal ({@sys.wifi.signal}).
- Connected to {@sys.wifi}. The signal is good: {@sys.wifi.signal}.

## When it's weak

- You're on {@sys.wifi}, but the signal is weak ({@sys.wifi.signal}): things may be slow. Moving closer to the router would help.

## When it's not connected

- Wi-Fi is on, but you're not connected to any network. I can see {@sys.wifi.count} around.

## When it's off

- I see no Wi-Fi network at all: Wi-Fi is probably off.
