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
- **29 skills** in `termnl/languages/en/skills/`, one per action + object. Reading skills name a reader
  (`reads: memory`) and write a reply per level (`## When it's high`); the reader gives values, a level
  and sometimes a table. Two ways to read, both chosen by Gab on 22 Oct: the reader reads the device
  itself (memory, temperature, storage, the clock), or the skill keeps its command, which runs and is
  shown, and the reader turns its output into words (Wi-Fi, networks around, the address, Bluetooth).
  "Am I online" means connected to a network: nothing leaves the device to ask the internet.
- **Rules learned from Gab's own sentences**, each with tests (`tests/test_dialogue.py`): names never
  swallow a place; misspelled device values are confirmed; typos are read as known words only when that
  reads better, and said; names are never corrected; "not/don't" requests are asked about; approval comes
  last, with every value known; a lone yes/no with nothing waiting says so; a new name never replaces
  what's there.
- **Logs:** `logs/<date>.jsonl` holds every turn Gab typed (not in git). They are the honest test set.

- **Gab's real sentences:** `tests/real.md` (kept out of git: his typos are on purpose, and he doesn't
  want them read as misleading his model) holds his conversations from the logs, each turn with what
  TermNL should do: `should (Claude):` is a guess waiting for his word. `python3 -m tests.real -v`
  replays them; `--add` brings in new days.

Run: `python3 -m termnl.check` · `python3 -m unittest` (67 pass) · `python3 -m tests.measure -v`
(59 phrasings: 29 handled, 22 asked first, 4 wrong skill but asked, 0 wrong actions, 4 not understood:
"can I get the browser" fell under the line after retraining; Gab: leave it, you don't "get" an app;
then his 117 real turns: 95 as Claude guessed).

## Next

- `briefs/2026-10-22-clock-network-real-tests.md`: done on 22 Oct, evening.
- **A question for Gab: should reading ever ask first?** Reading changes nothing, yet "list", "threads",
  "wha time is it" ask "Do you want me to…?", and when unsure about a bare object ("wifi access", "do i
  have bluetooth") the model guesses a change and asks about it. Most differences in `tests/real.md` come
  from this. His call before building.
- `briefs/2026-10-22-model-format.md`: a lighter model and how to package it, to discuss with Gab first.
- Push to talk was tried on 22 Oct and removed: Brave's on-device speech model never downloaded, and its
  default speech service didn't work either.
