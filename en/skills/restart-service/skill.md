---
does: restart service
label: restart a service
admin: yes
approve: no
---

## Sentences

- <restart> [the] {name} [<service>]
- <restart> [the|a] <service>

## Values

- name: @sys.service, required

## Command

systemctl restart {name}

## Replies

- ask name: Which service? | Which service should I restart?
- approve: Restart {name}?
- done: {name} restarted. | Done, {name} is restarting.
