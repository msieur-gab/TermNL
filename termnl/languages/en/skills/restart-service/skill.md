---
does: restart service
label: restart a service
admin: yes
approve: no
---

## Words

- bounce, kick → restart

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
- bounce nginx
- can you restart the bluetooth service
- nginx is stuck, restart it
- kick the music server
- I'd like mpd restarted
- please restart the web server, it stopped answering
- relaunch ssh

## What it needs

- {name}: a service on the device. If it's missing, ask: Which service? | Which service should I restart?

## Command

systemctl restart {name}

## Replies

- approve: Restart {name}?
- done: {name} restarted. | Done, {name} is restarting.
