---
does: connect wifi
label: join a Wi-Fi network
admin: no
approve: yes
waits: 60
---

## People say

- connect to (the) {network} (wifi)
- connect to (the) wifi (called/named) {network}
- connect to (a/the) wifi

## Also said

- join cafe-guest
- get me on the home-5g network, I have the password
- log into the cafe-guest Wi-Fi with the password they gave me
- switch to the home-5g wifi
- I'm at the café, please hook me up to cafe-guest
- connect wifi home-5g with password
- use the cafe-guest network, here's the password

## What it needs

- {network}: a network around. If it's missing, ask: Which network? | Which Wi-Fi should I join?
- {password}: a secret. If it's missing, ask: What's the password? | What's the Wi-Fi password?

## Command

termnl-wifi join {network}

## Replies

- approve: Join {network}? If you're reaching me over another network, we may lose the connection.
- done: Connected to {network}. | Done, I'm on {network}.
