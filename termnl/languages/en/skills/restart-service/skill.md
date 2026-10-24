---
does: restart service
label: restart a service
admin: yes
approve: no
---

## Sentences

- `<restart> [the] {name} [<service>]`
- `<restart> [the|a] <service>`

## Also said

- restart a service
- restart nginx please
- relaunch the web server
- give mpd a restart
- the music server needs restarting
- turn ssh off and on again
- can you restart the music server

## Values

- name: @sys.service, required

## Command

systemctl restart {name}

## Replies

- ask name: Which service? | Which service should I restart?
- approve: Restart {name}?
- done: {name} restarted. | Done, {name} is restarting.
