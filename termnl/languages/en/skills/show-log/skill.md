---
does: show log
label: show a service's log
admin: no
approve: no
---

## People say

- show (me) (the) log of (the) {name} (service)
- show (me) (the) {name} log
- why did (the) {name} (service) fail
- show (a/the) log

## Also said

- show the nginx log
- why did mpd fail?
- what does the web server's log say
- the music server crashed, can you show me its log
- let me read the end of the nginx log to see what went wrong
- mpd log please
- what errors did ssh write in its log recently

## What it needs

- {name}: a service on the device. If it's missing, ask: Which service? | Whose log should I show?

## Command

journalctl -u {name} -n 20 --no-pager

## Replies

- done: The last lines of {name}'s log: {output} | {name}'s log ends with: {output}
