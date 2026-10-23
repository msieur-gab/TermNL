---
does: check network
label: check the network
reads: network
admin: no
approve: no
---

## Sentences

- `am i (online|connected) [to the internet]`
- `is the <network> (working|up|on)`
- `(what's|what is) my ip [address]`
- `<check> [the|my] <network>`

## Also said

- what is my ip address
- my ip
- am i online
- is the network up
- network status
- ip address

## Command

ip -4 -brief addr

## When it's connected

- You're connected through {@sys.network.through}. Your address on this network is {@sys.network.address}. I only look at the board itself, so I can't tell whether the internet answers.
- Connected through {@sys.network.through}, at {@sys.network.address}. (I don't contact anything outside to check the internet.)

## When it's not connected

- You're not connected to any network: no Wi-Fi and no cable has an address.
