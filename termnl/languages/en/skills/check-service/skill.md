---
does: check service
label: check a service
admin: no
approve: no
---

## People say

- is (the) {name} (service) running/working/up/on
- check (the) {name} service
- check (the/a) service

## Also said

- check a service
- is the web server up
- check nginx
- is the music server working
- is mpd running
- status of ssh
- is nginx still alive

## What it needs

- {name}: a service on the device. If it's missing, ask: Which service? | Which service should I check?

## Command

systemctl is-active {name}

## Replies

- done: {name}: {output}
