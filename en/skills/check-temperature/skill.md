---
does: check temperature
label: check the temperature
admin: no
approve: no
---

## Sentences

- `is the <system> (too hot|overheating|hot)`
- `how hot is the <system>`
- `(what's|what is) the <temperature> [of the <system>]`
- `<check> [the] <temperature>`

## Command

cat /sys/class/thermal/thermal_zone0/temp

## Replies

- done: Temperature: {output} | It's at {output}
