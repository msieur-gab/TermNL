---
does: check service
label: check a service
admin: no
approve: no
---

## Sentences

- is [the] {name} [<service>] (running|working|up|on)
- <check> [the] {name} <service>
- <check> [the|a] <service>

## Values

- name: @sys.service, required

## Command

systemctl is-active {name}

## Replies

- ask name: Which service? | Which service should I check?
- done: {name}: {output}
