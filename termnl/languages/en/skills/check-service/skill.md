---
does: check service
label: check a service
admin: no
approve: no
---

## Sentences

- `is [the] {name} [<service>] (running|working|up|on)`
- `<check> [the] {name} <service>`
- `<check> [the|a] <service>`

## Also said

- check a service
- is the web server up
- check nginx
- is the music server working
- is mpd running
- status of ssh
- is nginx still alive

## Values

- name: @sys.service, required

## Command

systemctl is-active {name}

## Replies

- ask name: Which service? | Which service should I check?
- done: {name}: {output}
