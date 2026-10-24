---
does: check time
label: check the time
reads: clock
admin: no
approve: no
---

Gab, 22 Oct: "what time is it?" (four times), "what is the date today". On a board the time is a fact
about the machine: without a clock battery, it can be wrong after a power cut.

## Sentences

- `what time is it [now]`
- `(what's|what is) the (time|date|day) [today|now]`
- `what (day|date) is it [today]`
- `(what's|what is) today's date`
- `<check> [the] <time>`

## Also said

- the time
- time please
- tell me the time
- check the time

## When it's fine

- It's {@sys.clock}, {@sys.clock.day} {@sys.clock.date}.
- {@sys.clock} on {@sys.clock.day} {@sys.clock.date}.

## When it's unsure

- It's {@sys.clock}, {@sys.clock.day} {@sys.clock.date}, as far as I know: my clock hasn't been set from a time server, so it may be a little off.

## When it's wrong

- My clock says {@sys.clock.date}, which can't be right: it was probably reset when the power went off. It usually sets itself again once the board is online.
