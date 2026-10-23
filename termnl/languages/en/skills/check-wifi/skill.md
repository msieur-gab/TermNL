---
does: check wifi
label: check Wi-Fi
reads: wifi
admin: no
approve: no
---

## Sentences

- `is [the] <wifi> (on|off|working)`
- `(which|what) <wifi> [network] am i (on|connected to)`
- `<check> [the] <wifi>`

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
