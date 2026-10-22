---
does: check network
label: check the network
admin: no
approve: no
---

## Sentences

- am i (online|connected) [to the internet]
- is the <network> (working|up|on)
- (what's|what is) my ip [address]
- <check> [the|my] <network>

## Command

ip -4 -brief addr

## Replies

- done: Network: {output} | Here's the connection: {output}
