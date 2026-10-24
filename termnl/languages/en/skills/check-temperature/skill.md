---
does: check temperature
label: check the temperature
reads: temperature
admin: no
approve: no
---

## People say

- is the system too hot
- is the system overheating
- is the system hot
- how hot is the system
- what's the temperature (of the system)
- what is the temperature (of the system)
- check (the) temperature

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
- Hey {user}, no problem: your CPU is at {@sys.temperature}, well below the {@sys.temperature.max} where it would slow down.

## When it's warm

- It's getting warm: {@sys.temperature}. Still fine, but keep an eye on it.
- {user}, it's getting warm: {@sys.temperature}. Still fine, but keep an eye on it.

## When it's hot

- It's hot: {@sys.temperature}, close to the {@sys.temperature.max} where it slows down. Give it some air.
- {user}, it's hot: {@sys.temperature}, close to the {@sys.temperature.max} where it slows down. Give it some air.
