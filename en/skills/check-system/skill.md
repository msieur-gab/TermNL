---
does: check system
label: check the board
admin: no
approve: no
---

## Sentences

- how is the <system> [doing]
- how's the <system> [doing]
- <check> [the] <system>
- [give me|run] [a] (health|system|status) (check|report)
- is everything (ok|okay|fine|alright) [with the <system>]
- <system> (status|health)

## Command

uptime && free -h && df -h / && cat /sys/class/thermal/thermal_zone0/temp

## Replies

- done: Here's how the board is doing: {output} | The board right now: {output}
