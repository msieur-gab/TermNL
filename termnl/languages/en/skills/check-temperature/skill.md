---
does: check temperature
label: check the temperature
reads: temperature
admin: no
approve: no
---

## Sentences

- `is the <system> (too hot|overheating|hot)`
- `how hot is the <system>`
- `(what's|what is) the <temperature> [of the <system>]`
- `<check> [the] <temperature>`

## Also said

- chip temperature
- cpu temperature
- is the board too hot
- is it overheating
- how warm is the cpu
- is the pi hot
- board temperature
- my board is warm
- the device feels hot
- temperature
- how hot is the board
- check the heat
- is the cpu cooking
- what temperature is the chip at
- is the processor running hot
- tell me how warm the board is
- is it getting too warm in there

## When it's fine

- No worries, it's at {@sys.temperature}, well below the {@sys.temperature.max} where it would slow down.
- {@sys.temperature}. All good.

## When it's warm

- It's getting warm: {@sys.temperature}. Still fine, but keep an eye on it.

## When it's hot

- It's hot: {@sys.temperature}, close to the {@sys.temperature.max} where it slows down. Give it some air.
