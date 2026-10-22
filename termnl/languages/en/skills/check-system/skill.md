---
does: check system
label: check the board
reads: health
admin: no
approve: no
---

## Sentences

- `how is the <system> [doing]`
- `how's the <system> [doing]`
- `<check> [the] <system>`
- `[give me|run] [a] (health|system|status) (check|report)`
- `is everything (ok|okay|fine|alright) [with the <system>]`
- `<system> (status|health)`

## When it's fine

- All good. It has been running for {@sys.health.uptime}.
- Everything looks fine.

## When it's busy

- It works, but it's busy: have a look at what's marked below.

## When it's struggling

- It's struggling: something below needs your attention.
