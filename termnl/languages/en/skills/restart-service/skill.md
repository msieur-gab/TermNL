---
does: restart service
label: restart a service
admin: yes
approve: no
---

## People say

- restart (the) {name} (service)
- restart (the/a) service

## Also said

- restart a service
- restart nginx please
- relaunch the web server
- give mpd a restart
- the music server needs restarting
- turn ssh off and on again
- can you restart the music server

## What it needs

- {name}: a service on the device. If it's missing, ask: Which service? | Which service should I restart?

## Command

systemctl restart {name}

## Replies

- approve: Restart {name}?
- done: {name} restarted. | Done, {name} is restarting.
