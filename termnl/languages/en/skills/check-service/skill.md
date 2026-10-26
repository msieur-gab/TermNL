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
- is the ssh service on right now
- can you see if nginx is up
- mpd status?
- is the music server still going
- I'd like to know if the web server is working
- is there a way to tell whether mpd is alive
- my website won't load, is nginx running
- I can't log in remotely, is ssh up

## What it needs

- {name}: a service on the device. If it's missing, ask: Which service? | Which service should I check?

## Command

systemctl is-active {name}

## Replies

- done: {name}: {output}
