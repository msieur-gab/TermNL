# Handoff — 22 October 2026, afternoon

TermNL (born this morning as TermLU, from ptiLU). The design lives in Gab's brain repo, `projects/termlu/`:
read `intention.md`, `brief.md`, `decisions.md`, `review-2026-10-22.md`, both `prior-art-2026-10-22*.md`
and the `open-question-*.md` files before changing anything, and the `.inbox.md` for what Gab said today
that isn't ratified yet. Gab's decisions are his; don't rework them.

## What exists

- **Python only.** The first version in JavaScript was frozen (it gave the same replies as the Python one
  on 139 turns, commit c032e13), then deleted on Gab's request. See `README.md` for the layout.
- **The brain on the device:** `python3 -m termnl.server` serves the chat page and a thin API that takes
  sentences, never commands. Built and tested on Gab's laptop (my-laptop); files land in `~/TermNL-home`;
  restart, shutdown, Wi-Fi, Bluetooth and services are simulated (`settings.md`, `simulate:`).
- **28 skills** in `termnl/languages/en/skills/`, one per action + object. Reading skills name a reader
  (`reads: memory`) and write a reply per level (`## When it's high`); the reader gives values, a level
  and sometimes a table.
- **Rules learned from Gab's own sentences**, each with tests (`tests/test_dialogue.py`): names never
  swallow a place; misspelled device values are confirmed; typos are read as known words only when that
  reads better, and said; names are never corrected; "not/don't" requests are asked about; approval comes
  last, with every value known; a lone yes/no with nothing waiting says so; a new name never replaces
  what's there.
- **Logs:** `logs/<date>.jsonl` holds every turn Gab typed (not in git). They are the honest test set.

Run: `python3 -m termnl.check` · `python3 -m unittest` (60 pass) · `python3 -m tests.measure -v`
(59 phrasings: 29 handled, 23 asked first, 4 wrong skill but asked, 0 wrong actions, 3 not understood).

## Next

Gab picked the next tasks on 22 Oct; each has a brief in `briefs/`, written at the end of a long session
(read them as Claude's proposals, to check before trusting). Everything else is parked in `TODO.md`.

- `briefs/2026-10-22-clock-network-real-tests.md`: a clock skill, Wi-Fi/Bluetooth/network replies in plain
  words, a test set from Gab's real sentences.
- `briefs/2026-10-22-model-format.md`: a lighter model and how to package it, to discuss with Gab first.
